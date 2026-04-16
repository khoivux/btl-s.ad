"""
Seed: Mỗi customer có 2-6 completed orders.
Mỗi order có 1-3 items (random từ product-service).
Tất cả orders đều status=completed, payment=success, shipment=completed.

Chạy:
  docker cp order-service/seed_orders.py bookstore-micro05-order-service-1:/app/seed_orders.py
  docker exec bookstore-micro05-order-service-1 python seed_orders.py
"""
import os
import sys
import django
import random
import requests
import decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'order_service.settings')
sys.path.insert(0, '/app')
django.setup()

from app.models import Order, OrderItem, OrderStatusLog

PRODUCT_SERVICE_URL  = "http://product-service:8000"
PAY_SERVICE_URL      = "http://pay-service:8000"
SHIP_SERVICE_URL     = "http://ship-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"

SHIPPING_METHODS = ['economy', 'standard', 'fast']
SHIPPING_FEES    = {'economy': '1.00', 'standard': '2.50', 'fast': '5.00'}
PAYMENT_METHODS  = ['COD', 'BANK_TRANSFER', 'MOMO', 'VNPAY']
ADDRESSES = [
    "Nguyen Van A | 0901234567\n123 Nguyen Hue, District 1, Ho Chi Minh City, Vietnam",
    "Tran Thi B | 0912345678\n456 Le Loi, District 3, Ho Chi Minh City, Vietnam",
    "Le Van C | 0923456789\n789 Dinh Tien Hoang, Binh Thanh, Ho Chi Minh City, Vietnam",
    "Pham Thi D | 0934567890\n12 Tran Hung Dao, Hai Chau, Da Nang, Vietnam",
    "Hoang Van E | 0945678901\n99 Ba Trieu, Hoan Kiem, Ha Noi, Vietnam",
]


def clear_old_data():
    print("=== Clearing old order data ===")
    deleted_logs, _ = OrderStatusLog.objects.all().delete()
    deleted_items, _ = OrderItem.objects.all().delete()
    deleted_orders, _ = Order.objects.all().delete()
    print(f"  Deleted: {deleted_orders} orders, {deleted_items} items, {deleted_logs} logs")


def seed():
    clear_old_data()

    # 1. Lấy danh sách customers
    print("\n=== Fetching customers ===")
    try:
        cust_r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/", timeout=5)
        customers = cust_r.json() if cust_r.status_code == 200 else []
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    if not customers:
        print("  No customers found! Please seed customers first.")
        return
    print(f"  Found {len(customers)} customers")

    # 2. Lấy danh sách products
    print("\n=== Fetching products ===")
    try:
        prod_r = requests.get(f"{PRODUCT_SERVICE_URL}/products/?page_size=100", timeout=5)
        data = prod_r.json()
        products = data.get('results', data) if isinstance(data, dict) else data
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    if not products:
        print("  No products found! Please seed products first.")
        return
    print(f"  Found {len(products)} products")

    # 3. Seed orders
    print("\n=== Seeding orders ===")
    total_orders = 0

    for cust in customers:
        customer_id = cust['id']
        num_orders = random.randint(2, 6)

        for i in range(num_orders):
            # Random 1-3 items
            n_items = min(random.randint(1, 3), len(products))
            selected = random.sample(products, n_items)
            shipping_method = random.choice(SHIPPING_METHODS)
            payment_method  = random.choice(PAYMENT_METHODS)
            address         = random.choice(ADDRESSES)
            shipping_fee    = decimal.Decimal(SHIPPING_FEES[shipping_method])

            # Tính tổng tiền
            total = decimal.Decimal('0')
            items_data = []
            for p in selected:
                qty   = random.randint(1, 3)
                price = decimal.Decimal(str(p['price']))
                total += price * qty
                items_data.append({
                    'product_id':   p['id'],
                    'product_name': p['name'],
                    'item_image_url': p.get('image_url', ''),
                    'quantity':     qty,
                    'unit_price':   price,
                })

            total_with_ship = (total + shipping_fee).quantize(decimal.Decimal('0.00'))

            # Tạo Order
            order = Order.objects.create(
                customer_id     = customer_id,
                status          = 'completed',
                total_amount    = total_with_ship,
                shipping_address= address,
                shipping_fee    = shipping_fee,
                shipping_method = shipping_method,
                points_generated= int(total),
            )
            for it in items_data:
                OrderItem.objects.create(order=order, **it)

            # Status log (full flow)
            for s in ['pending_confirmation', 'processing', 'ready_for_pickup', 'delivering', 'completed']:
                OrderStatusLog.objects.create(order=order, status=s, notes='Seeded data')

            # Gọi pay-service
            try:
                pay_r = requests.post(f"{PAY_SERVICE_URL}/payments/", json={
                    'order_id':   order.id,
                    'customer_id': customer_id,
                    'amount':     str(total_with_ship),
                    'method':     payment_method,
                }, timeout=5)
                if pay_r.status_code not in (200, 201):
                    print(f"    [WARN] Pay-service returned {pay_r.status_code} for order {order.id}")
            except Exception as e:
                print(f"    [WARN] Pay-service error: {e}")

            # Gọi ship-service
            try:
                ship_r = requests.post(f"{SHIP_SERVICE_URL}/shipments/", json={
                    'order_id':       order.id,
                    'customer_id':    customer_id,
                    'address':        address,
                    'shipping_method': shipping_method,
                    'status':         'completed',
                }, timeout=5)
                if ship_r.status_code not in (200, 201):
                    print(f"    [WARN] Ship-service returned {ship_r.status_code} for order {order.id}")
            except Exception as e:
                print(f"    [WARN] Ship-service error: {e}")

            total_orders += 1
            print(f"  ✓ Customer #{customer_id} | Order #{order.id} | {n_items} items | ${total_with_ship} | {payment_method}")

    print(f"\n=== Seed completed: {total_orders} orders for {len(customers)} customers ===")


if __name__ == '__main__':
    seed()
