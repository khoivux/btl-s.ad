import requests
import random
import time

INTERACTION_SERVICE_URL = "http://interaction-service:8000"
PRODUCT_SERVICE_URL = "http://product-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"

ACTIONS = ["view_product", "search", "add_to_cart"]

def seed():
    print("=== Fetching customers and products ===")
    try:
        cust_r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=5)
        customers = cust_r.json()
        
        prod_r = requests.get(f"{PRODUCT_SERVICE_URL}/products/?page_size=100", timeout=5)
        products = prod_r.json().get('results', [])
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    if not customers or not products:
        print("  Missing customers or products.")
        return

    print(f"  Seeding interactions for {len(customers)} customers...")

    count = 0
    for cust in customers:
        user_id = cust['id']
        num_interactions = random.randint(5, 12)
        
        for _ in range(num_interactions):
            action = random.choice(ACTIONS)
            target = random.choice(products)
            
            target_id = str(target['id'])
            if action == 'search':
                target_id = target['name'][:10] # Search keyword
            
            payload = {
                "user_id": user_id,
                "action": action,
                "target_id": target_id
            }
            
            try:
                r = requests.post(f"{INTERACTION_SERVICE_URL}/logs/", json=payload, timeout=5)
                if r.status_code == 201:
                    count += 1
            except Exception as e:
                print(f"      [ERROR] {e}")
        
        print(f"  ✓ Customer #{user_id} seeded")

    print(f"\n=== Seed completed: {count} interactions logged ===")

if __name__ == '__main__':
    seed()
