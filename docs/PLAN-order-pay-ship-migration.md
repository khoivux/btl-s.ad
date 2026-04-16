# PLAN: Migrate Order / Pay / Ship Services → Product-Service

## Mục tiêu

Loại bỏ hoàn toàn tham chiếu đến `book-service` cũ trong `order-service`, `pay-service`, `ship-service`, `api-gateway` và frontend templates. Thay thế bằng `product-service` mới hỗ trợ 11 danh mục sản phẩm, JSONB attributes.

---

## Phân tích hiện trạng

### ✅ Không cần thay đổi logic
| Service | Lý do |
|---|---|
| `pay-service` | Chỉ làm việc với `order_id`, `amount` — không tham chiếu book/product |
| `ship-service` | Chỉ làm việc với `order_id`, `address` — không tham chiếu book/product |

### ❌ Cần sửa

| Service | File | Vấn đề |
|---|---|---|
| `order-service` | `models.py` | `OrderItem.book_id`, `OrderItem.book_title` — sai field name |
| `order-service` | `serializers.py` | Fields `book_id`, `book_title` hardcoded |
| `order-service` | `views.py` | `BOOK_SERVICE_URL` dùng để fetch giá và deduct inventory |
| `product-service` | `product_view.py` | Thiếu endpoint `/products/{id}/inventory/` |
| `api-gateway` | `views/orders.py` | `CheckoutPageView` gọi `BOOK_SERVICE_URL` |
| `api-gateway` | `templates/checkout.html` | `item.title`, `item.author` (book-centric) |
| `api-gateway` | `templates/order_detail.html` | `item.book_title`, `item.book_id` |
| `api-gateway` | `templates/order_history.html` | Có thể còn book-centric fields |

---

## Thứ tự thực hiện

```
Phase 0 → Data Reset & Seed  : Xóa dữ liệu cũ, tạo seed data mới
Phase 1 → product-service    : Thêm inventory endpoint
Phase 2 → order-service      : Rename model + migration + views
Phase 3 → api-gateway views  : CheckoutPageView
Phase 4 → frontend           : checkout.html, order_detail.html, order_history.html
Phase 5 → Restart & Verify
```

---

## Phase 0 — Data Reset & Seed

### Chiến lược

> **Xóa toàn bộ dữ liệu cũ** (order, payment, shipment) rồi tạo seed mới. Không cần giữ lại data cũ vì đang đổi schema (`book_id` → `product_id`).

### Bước 0.1 — Xóa dữ liệu cũ

Chạy trong từng container:

```bash
# order-service: xóa toàn bộ Order, OrderItem, OrderStatusLog
docker exec bookstore-micro05-order-service-1 python manage.py shell -c "
from app.models import Order, OrderItem, OrderStatusLog
OrderStatusLog.objects.all().delete()
OrderItem.objects.all().delete()
Order.objects.all().delete()
print('order-service cleared')
"

# pay-service: xóa Payment
docker exec bookstore-micro05-pay-service-1 python manage.py shell -c "
from app.models import Payment
Payment.objects.all().delete()
print('pay-service cleared')
"

# ship-service: xóa Shipment
docker exec bookstore-micro05-ship-service-1 python manage.py shell -c "
from app.models import Shipment
Shipment.objects.all().delete()
print('ship-service cleared')
"
```

### Bước 0.2 — Tạo Seed Script

**[NEW]** Tạo file `order-service/seed_orders.py`:

```python
"""
Seed: Mỗi customer có 2-6 completed orders.
Mỗi order có 1-3 items (random từ product-service).
Tất cả orders đều status=completed, payment=success, shipment=completed.

Chạy:
  docker exec bookstore-micro05-order-service-1 python seed_orders.py
"""
import os
import sys
import django
import random
import requests
import decimal
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/app')
django.setup()

from app.models import Order, OrderItem, OrderStatusLog

PRODUCT_SERVICE_URL = "http://product-service:8000"
PAY_SERVICE_URL     = "http://pay-service:8000"
SHIP_SERVICE_URL    = "http://ship-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"

SHIPPING_METHODS = ['economy', 'standard', 'fast']
PAYMENT_METHODS  = ['COD', 'BANK_TRANSFER', 'MOMO', 'VNPAY']
ADDRESSES = [
    "Nguyễn Văn A | 0901234567\n123 Nguyễn Huệ, Quận 1, TP. HCM, Vietnam",
    "Trần Thị B | 0912345678\n456 Lê Lợi, Quận 3, TP. HCM, Vietnam",
    "Lê Văn C | 0923456789\n789 Đinh Tiên Hoàng, Bình Thạnh, TP. HCM, Vietnam",
    "Phạm Thị D | 0934567890\n12 Trần Hưng Đạo, Đà Nẵng, Vietnam",
]

def seed():
    # 1. Lấy danh sách customers
    cust_r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/")
    customers = cust_r.json() if cust_r.status_code == 200 else []
    if not customers:
        print("No customers found!")
        return

    # 2. Lấy danh sách products
    prod_r = requests.get(f"{PRODUCT_SERVICE_URL}/products/?page_size=100")
    products = prod_r.json().get('results', []) if prod_r.status_code == 200 else []
    if not products:
        print("No products found!")
        return

    print(f"Seeding for {len(customers)} customers with {len(products)} products...")

    for cust in customers:
        customer_id = cust['id']
        num_orders = random.randint(2, 6)

        for _ in range(num_orders):
            # Random 1-3 sản phẩm
            selected = random.sample(products, min(random.randint(1, 3), len(products)))
            shipping_method = random.choice(SHIPPING_METHODS)
            payment_method = random.choice(PAYMENT_METHODS)
            address = random.choice(ADDRESSES)
            shipping_fee = decimal.Decimal({'economy': '1.0', 'standard': '2.5', 'fast': '5.0'}[shipping_method])

            # Tính tổng
            total = decimal.Decimal('0')
            items_data = []
            for p in selected:
                qty = random.randint(1, 3)
                price = decimal.Decimal(str(p['price']))
                total += price * qty
                items_data.append({
                    'product_id': p['id'],
                    'product_name': p['name'],
                    'quantity': qty,
                    'unit_price': price,
                })

            total_with_ship = (total + shipping_fee).quantize(decimal.Decimal('0.00'))

            # Tạo Order
            order = Order.objects.create(
                customer_id=customer_id,
                status='completed',
                total_amount=total_with_ship,
                shipping_address=address,
                shipping_fee=shipping_fee,
                shipping_method=shipping_method,
                points_generated=int(total),
            )
            for it in items_data:
                OrderItem.objects.create(order=order, **it)

            # Status log
            for s in ['pending_confirmation', 'processing', 'ready_for_pickup', 'delivering', 'completed']:
                OrderStatusLog.objects.create(order=order, status=s)

            # Tạo Payment (call pay-service)
            try:
                requests.post(f"{PAY_SERVICE_URL}/payments/", json={
                    'order_id': order.id,
                    'customer_id': customer_id,
                    'amount': str(total_with_ship),
                    'method': payment_method,
                    'status': 'success',
                })
            except Exception as e:
                print(f"  Pay error: {e}")

            # Tạo Shipment (call ship-service)
            try:
                requests.post(f"{SHIP_SERVICE_URL}/shipments/", json={
                    'order_id': order.id,
                    'customer_id': customer_id,
                    'address': address,
                    'shipping_method': shipping_method,
                    'status': 'completed',
                })
            except Exception as e:
                print(f"  Ship error: {e}")

            print(f"  ✓ Customer #{customer_id} → Order #{order.id} ({len(items_data)} items, ${total_with_ship})")

    print("\nSeed completed!")

if __name__ == '__main__':
    seed()
```

### Bước 0.3 — Chạy Seed

```bash
# Copy seed script vào container và chạy
docker cp order-service/seed_orders.py bookstore-micro05-order-service-1:/app/seed_orders.py
docker exec bookstore-micro05-order-service-1 python seed_orders.py
```

### Kết quả mong đợi

| Data | Số lượng |
|---|---|
| Orders | `<số customers> × (2~6)` ≈ vài chục orders |
| OrderItems | Mỗi order 1-3 items |
| Payments | 1 payment/order, status=`success` |
| Shipments | 1 shipment/order, status=`completed` |
| Tất cả orders | Status = `completed` |

---

## Phase 1 — product-service: Thêm Inventory Endpoint

### [MODIFY] `product-service/modules/catalog/presentation/api/views/product_view.py`

Thêm class mới:

```python
class ProductInventoryView(APIView):
    """
    POST /products/<id>/inventory/
    Body: { "change": -N }  # âm = giảm stock, dương = tăng stock
    """
    def post(self, request, pk):
        repo = PostgresProductRepository()
        product = repo.get_by_id(pk)
        if not product:
            return Response({'error': 'Product not found'}, status=404)
        change = int(request.data.get('change', 0))
        new_stock = product.stock + change
        if new_stock < 0:
            return Response({'error': 'Insufficient stock'}, status=400)
        repo.update(pk, {'stock': new_stock})
        return Response({'id': pk, 'stock': new_stock})
```

### [MODIFY] `product-service/modules/catalog/presentation/api/urls.py`

```python
path('products/<int:pk>/inventory/', ProductInventoryView.as_view()),
```

---

## Phase 2 — order-service

### [MODIFY] `order-service/app/models.py`

```python
# Trước
class OrderItem(models.Model):
    book_id = models.IntegerField()
    book_title = models.CharField(max_length=255, default='')

# Sau
class OrderItem(models.Model):
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=255, default='')
```

### Migration

```bash
docker exec bookstore-micro05-order-service-1 python manage.py makemigrations app
docker exec bookstore-micro05-order-service-1 python manage.py migrate
```

### [MODIFY] `order-service/app/serializers.py`

```python
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_name', 'quantity', 'unit_price', 'subtotal']
```

### [MODIFY] `order-service/app/views.py`

Thay đổi:
- `BOOK_SERVICE_URL = "http://book-service:8000"` → `PRODUCT_SERVICE_URL = "http://product-service:8000"`
- **Step 2** (fetch product price):
  - `item['book_id']` → `item['product_id']`
  - `GET /books/{id}/` → `GET /products/{product_id}/`
  - `book.get('title', '')` → `product.get('name', '')`
  - `'book_id': ...` → `'product_id': ...`
  - `'book_title': ...` → `'product_name': ...`
- **Step 4.5** (inventory deduction):
  - `POST /books/{id}/inventory/` → `POST /products/{id}/inventory/`
- **CheckPurchase view**:
  - Param `book_id` → `product_id`
  - `OrderItem.objects.filter(book_id=book_id)` → `filter(product_id=product_id)`

---

## Phase 3 — api-gateway: CheckoutPageView

### [MODIFY] `api_gateway/app/views/orders.py`

```python
# Thêm/sửa constants
PRODUCT_SERVICE_URL = "http://product-service:8000"
# Xóa hoặc không dùng BOOK_SERVICE_URL

# Trong CheckoutPageView.get():
for item in raw_items:
    self.service_url = PRODUCT_SERVICE_URL
    prod_r = self.proxy_request(request, f"products/{item['product_id']}/", method="GET")
    product = prod_r.json() if prod_r and prod_r.status_code == 200 else {}
    
    subtotal = float(product.get('price', 0)) * item['quantity']
    total += subtotal
    cart_items.append({
        'product_id': item['product_id'],
        'name': product.get('name', ''),
        'category_name': product.get('category_name', ''),
        'image_url': product.get('image_url', ''),
        'price': product.get('price', 0),
        'quantity': item['quantity'],
        'subtotal': round(subtotal, 2),
    })
```

---

## Phase 4 — Frontend Templates

### [MODIFY] `checkout.html`

```diff
- <p>{{ item.title }}</p>
- <p>{{ item.author }}</p>
+ <p>{{ item.name }}</p>
+ <p class="text-slate-400 text-xs">{{ item.category_name }}</p>
```

### [MODIFY] `order_detail.html`

```diff
- <h4>{{ item.book_title }}</h4>
- <p>ID: #{{ item.book_id }}</p>
+ <h4>{{ item.product_name }}</h4>
+ <a href="/products/{{ item.product_id }}/">View Product</a>
```

### [MODIFY] `order_history.html`

- Kiểm tra và đổi `book_title` → `product_name` nếu có

---

## Migration Strategy

> **Quan trọng**: `OrderItem` có dữ liệu sẵn trong DB. Dùng `RenameField` trong migration để không mất data:

```python
# Trong file migration được tạo tự động, Django sẽ tạo RenameField:
class Migration(migrations.Migration):
    operations = [
        migrations.RenameField(model_name='orderitem', old_name='book_id', new_name='product_id'),
        migrations.RenameField(model_name='orderitem', old_name='book_title', new_name='product_name'),
    ]
```

---

## Verification Checklist

- [ ] `product-service` phản hồi `POST /products/{id}/inventory/` đúng cách
- [ ] `order-service` khởi động không lỗi (migration thành công)
- [ ] Tạo order mới qua UI → order trong DB có `product_id` (không phải `book_id`)
- [ ] `order_detail.html` hiển thị `product_name` đúng
- [ ] Staff "Ready for Pickup" → ship-service vẫn hoạt động bình thường
- [ ] `CheckPurchase` API trả về đúng khi query theo `product_id`

---

## Rủi ro & Mitigation

| Rủi ro | Mitigation |
|---|---|
| Order cũ có `book_id`, migration rename conflict | `RenameField` giữ nguyên data, chỉ đổi tên column |
| product-service thiếu inventory endpoint | Thêm ở Phase 1 trước |
| Checkout fail vì field name khác | Test sau từng phase |
| `CheckPurchase` API bị break (frontend dùng `book_id` param) | Giữ backward-compat bằng cách accept cả `book_id` và `product_id` |
