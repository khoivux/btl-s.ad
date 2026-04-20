import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_ecommerce_data(num_users=500, num_products=200, num_interactions=20000):
    user_ids = [i for i in range(1, num_users + 1)]
    product_ids = [i for i in range(1, num_products + 1)]
    
    actions = [
        'view', 'click', 'add_to_cart', 'remove_from_cart', 
        'purchase', 'wishlist', 'review', 'share'
    ]
    
    # Action probabilities (rough funnel mapping)
    action_weights = [0.4, 0.25, 0.15, 0.05, 0.05, 0.05, 0.03, 0.02]
    
    start_date = datetime.now() - timedelta(days=30)
    
    data = []
    
    print(f"Generating data with {num_users} users and {num_products} products...")
    
    for _ in range(num_interactions):
        user = random.choice(user_ids)
        product = random.choice(product_ids)
        
        # Simulate realistic sequences for the same user-product combo.
        # e.g., if we decide to generate a purchase, we should prepend view, click, add_to_cart.
        sequence_choice = random.choices(['bounce', 'browse', 'cart', 'buy'], weights=[0.5, 0.25, 0.15, 0.1])[0]
        
        base_time = start_date + timedelta(days=random.randint(0, 29), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        if sequence_choice == 'bounce':
            data.append([user, product, 'view', base_time.isoformat()])
        elif sequence_choice == 'browse':
            data.append([user, product, 'view', base_time.isoformat()])
            base_time += timedelta(seconds=random.randint(10, 60))
            data.append([user, product, 'click', base_time.isoformat()])
            if random.random() < 0.2:
                base_time += timedelta(seconds=random.randint(10, 60))
                data.append([user, product, 'wishlist', base_time.isoformat()])
        elif sequence_choice == 'cart':
            data.append([user, product, 'view', base_time.isoformat()])
            base_time += timedelta(seconds=random.randint(10, 60))
            data.append([user, product, 'click', base_time.isoformat()])
            base_time += timedelta(seconds=random.randint(30, 120))
            data.append([user, product, 'add_to_cart', base_time.isoformat()])
            if random.random() < 0.3:
                base_time += timedelta(seconds=random.randint(60, 300))
                data.append([user, product, 'remove_from_cart', base_time.isoformat()])
        elif sequence_choice == 'buy':
            data.append([user, product, 'view', base_time.isoformat()])
            base_time += timedelta(seconds=random.randint(10, 60))
            data.append([user, product, 'click', base_time.isoformat()])
            base_time += timedelta(seconds=random.randint(30, 120))
            data.append([user, product, 'add_to_cart', base_time.isoformat()])
            base_time += timedelta(seconds=random.randint(60, 500))
            data.append([user, product, 'purchase', base_time.isoformat()])
            if random.random() < 0.5:
                base_time += timedelta(days=random.randint(1, 4))
                data.append([user, product, 'review', base_time.isoformat()])
            if random.random() < 0.2:
                base_time += timedelta(minutes=random.randint(5, 30))
                data.append([user, product, 'share', base_time.isoformat()])

    df = pd.DataFrame(data, columns=['user_id', 'product_id', 'action', 'timestamp'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp').reset_index(drop=True)
    
    # Save the dataset
    df.to_csv('data_user500.csv', index=False)
    print(f"Generated {len(df)} interaction rows.")
    print("Dataset saved to data_user500.csv")

if __name__ == "__main__":
    generate_ecommerce_data()
