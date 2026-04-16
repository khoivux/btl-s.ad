import os
import requests
from pymongo import MongoClient

def sync_all():
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://mongodb:27017/")
    client = MongoClient(MONGO_URL)
    db = client['bookstore']
    products_collection = db['products']
    
    # Try fetch products locally via service network if running in docker
    product_service_url = os.environ.get("PRODUCT_SERVICE_URL", "http://product-service:8000")
    print(f"Fetching products from: {product_service_url}/products/")
    
    try:
        r = requests.get(f"{product_service_url}/products/", timeout=10)
        items = r.json()
        
        count = 0
        for item in items.get('results', items) if isinstance(items, dict) else items:
            p_id = item.get('id')
            if not p_id:
                continue
                
            item['_id'] = p_id
            if 'id' in item:
                del item['id']
            
            products_collection.replace_one({'_id': p_id}, item, upsert=True)
            count += 1
            
        print(f"Synced {count} products from product-service to MongoDB.")
        
        # Ensure indices
        products_collection.create_index([("name", "text"), ("description", "text")])
        print("Text index created successfully.")
    except Exception as e:
        print(f"Error syncing products: {e}")

if __name__ == "__main__":
    sync_all()
