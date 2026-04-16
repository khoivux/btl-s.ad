import os
from django.conf import settings
from neo4j import GraphDatabase

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'none')

class Neo4jDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jDBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self._initialized = True

    def close(self):
        self.driver.close()

    def merge_user(self, user_id):
        query = """
        MERGE (u:User {id: $user_id})
        RETURN u
        """
        with self.driver.session() as session:
            session.run(query, user_id=user_id)

    def merge_product(self, product_id, title, category):
        query = """
        MERGE (p:Product {id: $product_id})
        SET p.title = $title
        MERGE (c:Category {name: $category})
        MERGE (p)-[:BELONGS_TO]->(c)
        RETURN p
        """
        with self.driver.session() as session:
            session.run(query, product_id=product_id, title=title, category=category)

    def record_interaction(self, user_id, product_id, action, weight=1.0):
        """
        Records an interaction between User and Product.
        action can be 'VIEWED', 'SEARCHED', 'CART', 'PURCHASED'
        """
        # Ensure nodes exist
        self.merge_user(user_id)
        
        # We assume the product is merged separately or we just merge by ID here if it doesn't exist
        query = f"""
        MATCH (u:User {{id: $user_id}})
        MERGE (p:Product {{id: $product_id}})
        MERGE (u)-[r:{action.upper()}]->(p)
        SET r.weight = $weight, r.timestamp = timestamp()
        RETURN r
        """
        with self.driver.session() as session:
            session.run(query, user_id=user_id, product_id=product_id, weight=weight)

    def get_user_interactions(self, user_id, limit=20):
        """
        Gets sequential interactions of a user to construct input for LSTM
        """
        query = """
        MATCH (u:User {id: $user_id})-[r]->(p:Product)
        RETURN type(r) as action, p.id as product_id, r.timestamp as timestamp
        ORDER BY r.timestamp DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            result = session.run(query, user_id=user_id, limit=limit)
            return [{"action": record["action"], "product_id": record["product_id"], "timestamp": record["timestamp"]} for record in result]

    def get_recommendation_context(self, user_id):
        """
        GraphRAG Retrieval: Finds items viewed/bought by similar users.
        """
        query = """
        MATCH (u:User {id: $user_id})-[:VIEWED|CART|PURCHASED]->(p:Product)<-[:VIEWED|CART|PURCHASED]-(other:User)-[:VIEWED|CART|PURCHASED]->(rec:Product)
        WHERE NOT (u)-[:VIEWED|CART|PURCHASED]->(rec)
        RETURN rec.id as product_id, rec.title as title, count(*) as freq
        ORDER BY freq DESC
        LIMIT 10
        """
        with self.driver.session() as session:
            result = session.run(query, user_id=user_id)
            return [{"product_id": record["product_id"], "title": record["title"], "freq": record["freq"]} for record in result]
            
    def get_direct_interactions_context(self, user_id):
        """
        Gets the recent things this user interacted with for prompt context
        """
        query = """
        MATCH (u:User {id: $user_id})-[r]->(p:Product)
        RETURN type(r) as action, p.title as title
        ORDER BY r.timestamp DESC
        LIMIT 5
        """
        with self.driver.session() as session:
            result = session.run(query, user_id=user_id)
            return [{"action": record["action"], "title": record["title"]} for record in result]

# Singleton access
neo4j_db = Neo4jDBManager()
