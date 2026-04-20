from neo4j import GraphDatabase
import pandas as pd
import os

class Neo4jBuilder:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def build_graph(self, csv_path):
        print(f"[INFO] Connecting to Neo4j to build graph from {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Clean up existing database for a fresh start
        with self.driver.session() as session:
            print("[INFO] Clearing existing specific nodes/relations (if any)...")
            session.run("MATCH (n:User) DETACH DELETE n")
            session.run("MATCH (n:Product) DETACH DELETE n")

            print("[INFO] Creating constraints and indexes...")
            session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
            session.run("CREATE CONSTRAINT prod_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE")

            # Extract unique users and products
            unique_users = df['user_id'].unique().tolist()
            unique_prods = df['product_id'].unique().tolist()

            print(f"[INFO] Creating {len(unique_users)} User nodes and {len(unique_prods)} Product nodes...")
            
            # Create Users
            session.run("""
                UNWIND $users AS user_id
                MERGE (u:User {id: user_id})
            """, users=unique_users)

            # Create Products
            session.run("""
                UNWIND $prods AS prod_id
                MERGE (p:Product {id: prod_id})
            """, prods=unique_prods)

            # Create Interaction Relationships using batching
            print(f"[INFO] Creating interaction relationships...")
            # Optimization: create generic INTERACTED_WITH and store action as property
            records = df[['user_id', 'product_id', 'action', 'timestamp']].to_dict('records')
            
            # Batch creation in chunks of 5000
            for i in range(0, len(records), 5000):
                batch = records[i:i+5000]
                session.run("""
                    UNWIND $batch AS record
                    MATCH (u:User {id: record.user_id})
                    MATCH (p:Product {id: record.product_id})
                    MERGE (u)-[r:INTERACTED_WITH {action: record.action}]->(p)
                    ON CREATE SET r.timestamp = record.timestamp
                    ON MATCH SET r.timestamp = record.timestamp
                """, batch=batch)
                print(f"  > Merged {min(i+5000, len(records))}/{len(records)} relationships...")
                
            print("\n[INFO] Basic interactions created. Now deducing User-User similarity...")
            # Deduce SIMILAR_TO relationship
            # Definition: User A is SIMILAR_TO User B if they interacted with at least 3 common products.
            # We add a weight property to SIMILAR_TO indicating how many common products they share.
            sim_query = """
            MATCH (u1:User)-[:INTERACTED_WITH]->(p:Product)<-[:INTERACTED_WITH]-(u2:User)
            WHERE u1.id < u2.id
            WITH u1, u2, count(DISTINCT p) as common_prods
            WHERE common_prods >= 5
            MERGE (u1)-[s:SIMILAR_TO]-(u2)
            SET s.weight = common_prods
            RETURN count(s) as new_relations
            """
            result = session.run(sim_query)
            record = result.single()
            if record:
                print(f"[SUCCESS] Inferred and created {record['new_relations']} SIMILAR_TO relationships between users!")
            
if __name__ == '__main__':
    # Local execution maps to localhost:7687 or neo4j:7687 within compose
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "none")
    # For Docker with auth=none, password can be ignored by driver or just empty.
    builder = Neo4jBuilder(uri=neo4j_uri, user=neo4j_user, password="")
    
    data_path = '../../data_user500.csv'
    if not os.path.exists(data_path):
        data_path = 'data_user500.csv'
        if not os.path.exists(data_path):
            data_path = "c:/bookstore-micro05/recommender-ai-service/data_user500.csv"
            
    builder.build_graph(data_path)
    builder.close()
