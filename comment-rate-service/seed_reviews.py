import os
import sys
import django
import random
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comment_rate_service.settings')
sys.path.insert(0, '/app')
django.setup()

from app.models import Review

ORDER_SERVICE_URL = "http://order-service:8000"

REVIEW_TEMPLATES = [
    "Great product! High quality and fast delivery.",
    "Very satisfied with this purchase.",
    "Exactly as described. Worth the money.",
    "Good quality, fits well.",
    "Highly recommended!",
    "Decent product for the price.",
    "Perfect, exactly what I was looking for.",
    "Super fast shipping and great item.",
    "I love this! Will buy again.",
    "Impressive quality, really impressed."
]

def seed():
    print("=== Clearing old reviews ===")
    Review.objects.all().delete()

    print("\n=== Fetching completed orders from order-service ===")
    try:
        # Lấy tất cả orders completed
        r = requests.get(f"{ORDER_SERVICE_URL}/orders/?status=completed&page_size=100", timeout=10)
        orders = r.json().get('results', []) if r.status_code == 200 else []
    except Exception as e:
        print(f"  ERROR fetching orders: {e}")
        return

    if not orders:
        print("  No completed orders found! Please seed order-service first.")
        return

    print(f"  Found {len(orders)} completed orders. Seeding reviews...")
    
    review_count = 0
    for order in orders:
        customer_id = order['customer_id']
        # Lấy items từ đơn hàng
        items = order.get('items', [])
        
        for item in items:
            product_id = item['product_id']
            
            # 70% chance to leave a review
            if random.random() < 0.7:
                comment = random.choice(REVIEW_TEMPLATES)
                rating = random.randint(4, 5) # Happy customers
                
                # Upsert review
                review, created = Review.objects.update_or_create(
                    customer_id=customer_id,
                    product_id=product_id,
                    defaults={
                        'rating': rating,
                        'comment': comment,
                        'customer_name': f"Customer #{customer_id}"
                    }
                )
                if created:
                    review_count += 1
                    print(f"  ✓ Review for Product #{product_id} by Customer #{customer_id}")

    print(f"\n=== Seed completed: {review_count} reviews created ===")

if __name__ == '__main__':
    seed()
