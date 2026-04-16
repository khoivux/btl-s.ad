# Kế hoạch Cập nhật: Chuyển đổi hệ thống sang `product-service`

Sau khi phân tích code, đây là toàn bộ các file cần sửa để các service khác (API Gateway, Cart, Catalog, Frontend) hoạt động đúng với `product-service` mới.

---

## 1. Cart Service

### [MODIFY] [views.py](file:///c:/bookstore-micro05/cart-service/app/views.py)
**Vấn đề:** `BOOK_SERVICE_URL = "http://book-service:8000"` đã dead. Logic validate sản phẩm gọi sai endpoint. Field `book_id` cũng cần hỗ trợ `product_id`.

**Thay đổi:**
- Đổi `BOOK_SERVICE_URL` → `PRODUCT_SERVICE_URL = "http://product-service:8000"`
- Sửa validate: Gọi `GET /products/{product_id}/` thay vì lấy toàn bộ list `/books/`
- Chấp nhận cả `book_id` và `product_id` trong payload để không phá frontend cũ

### [MODIFY] [models.py](file:///c:/bookstore-micro05/cart-service/app/models.py)
**Vấn đề:** Field `book_id` trong `CartItem` nên đổi tên thành `product_id` để rõ nghĩa.

**Thay đổi:**
- Đổi `book_id = IntegerField()` → `product_id = IntegerField()`
- Tạo migration mới

### [MODIFY] [serializers.py](file:///c:/bookstore-micro05/cart-service/app/serializers.py)
- Serializer tự động cập nhật theo Model (dùng `fields = '__all__'`) → Không cần sửa thêm

---

## 2. Catalog Service

### [MODIFY] [views.py](file:///c:/bookstore-micro05/catalog-service/app/views.py)
**Vấn đề:** `CatalogSyncView` nhận dữ liệu từ `book-service` (có các trường `title`, `author`...). Nay `product-service` gửi lên dữ liệu khác (`name`, `attributes` JSONB). Đồng thời URL sync trong `ProductModel._sync_to_mongo()` đang gọi `/sync/book/` nhưng catalog-service đang expose `/sync/`.

**Thay đổi:**
- Sửa `CatalogSyncView.post()` để nhận dữ liệu đa dạng hơn (lưu `name`, `description`, `attributes`, `category_id`, `price`, `stock`, `image_url`)
- Thêm endpoint `/sync/product/` và `/sync/product/<id>/` cho thống nhất với code `ProductModel._sync_to_mongo()`
- Cập nhật MongoDB text index: Thêm field `name`, `description` (thay cho `title`, `author`, `isbn` của Book)
- Đổi tên collection `books` → `products` trong MongoDB

### [MODIFY] [urls.py](file:///c:/bookstore-micro05/catalog-service/app/urls.py)
**Thay đổi:**
- Thêm routes `/sync/product/` và `/sync/product/<id>/`
- Giữ nguyên `/books/` và `/search/` để API Gateway không bị ảnh hưởng (hoặc thêm alias `/products/`)

---

## 3. API Gateway — Views

### [DELETE] [views/books.py](file:///c:/bookstore-micro05/api_gateway/app/views/books.py)
- File cũ sẽ bị xóa và thay thế hoàn toàn bằng file mới.

### [NEW] [views/products.py](file:///c:/bookstore-micro05/api_gateway/app/views/products.py)
**Lý do tạo mới:** Đổi tên từ `books.py` → `products.py` để phản ánh đúng bản chất đa sản phẩm.

**Nội dung:**
- Đổi `BOOK_SERVICE_URL` → `PRODUCT_SERVICE_URL = "http://product-service:8000"`
- Đổi tên class: `BookListView` → `ProductListView`, `BookDetailView` → `ProductDetailView`, `BookSearchView` → `ProductSearchView`
- `ProductListView`: Lấy categories từ `PRODUCT_SERVICE_URL/categories/` thay vì `book-service`
- `ProductSearchView`: Tương tự
- `ProductDetailView`: Gọi log interaction với `product_id` thay vì `book_id`, hiển thị `product.name` thay `product.title`
- Giữ nguyên `BookReviewSubmitView` → đổi tên thành `ProductReviewSubmitView`

### [MODIFY] [views/cart.py](file:///c:/bookstore-micro05/api_gateway/app/views/cart.py)
**Vấn đề:** `CartView` đang fetch danh sách sách từ `book-service` để ghép thông tin vào item giỏ hàng.

**Thay đổi:**
- Đổi `BOOK_SERVICE_URL` → `PRODUCT_SERVICE_URL`
- `CartView.get()`: Fetch product details qua `GET /products/{product_id}/` thay vì lấy toàn bộ list sách
- Đổi key từ `book_id` → `product_id` trong mapping
- Đổi `item['title']` → `item['name']` (product dùng `name` thay vì `title`)
- `AddCartItemView.post()`: Đổi payload `book_id` → `product_id`

### [MODIFY] [views/staff.py](file:///c:/bookstore-micro05/api_gateway/app/views/staff.py)
**Vấn đề:** `StaffDashboardView` và `StaffCategoryAddView` đang gọi `book-service`.

**Thay đổi:**
- Đổi `service_url = BOOK_SERVICE_URL` → `service_url = PRODUCT_SERVICE_URL`
- Sửa `StaffDashboardView`: Gọi `GET /products/` thay vì `GET /books/`
- Sửa `StaffCategoryAddView/Modify`: Gọi đúng endpoint categories của product-service

---

## 4. API Gateway — URLs

### [MODIFY] [urls.py](file:///c:/bookstore-micro05/api_gateway/app/urls.py)
**Vấn đề:** Import từ `app.views.books` không còn tồn tại, các route URL đang dùng tên cũ `books`.

**Thay đổi:**
- Đổi import: `from app.views.books import ...` → `from app.views.products import ProductListView, ProductSearchView, ProductDetailView, ProductReviewSubmitView`
- Đổi route `/books/` → `/products/`, `/books/<book_id>/` → `/products/<int:product_id>/`
- Đổi route name: `book_list` → `product_list`, `book_detail` → `product_detail`
- Giữ route `/` (home) trỏ về `ProductListView`

---

## 5. Frontend Templates (HTML)

> [!IMPORTANT]
> Giao diện phải hiển thị được **tất cả 11 loại sản phẩm** trong cùng một layout. Bộ lọc theo danh mục (Category Filter) là tính năng bắt buộc. Các attributes JSONB hiển thị linh hoạt theo từng loại.

### [MODIFY] [books.html](file:///c:/bookstore-micro05/api_gateway/app/templates/books.html) → đổi tên thành `products.html`
**Thay đổi layout chính:**
- Đổi tên file → `products.html`, tiêu đề trang → "All Products"
- Đổi field `book.title` → `product.name`, `book.author` → lấy từ `product.attributes`
- **Thêm thanh bộ lọc Category (Category Filter Bar):**
  - Hiển thị 11 danh mục như các chip/tab có thể click: `All | Book | Laptop | Mobile | ...`
  - Click vào danh mục → filter URL thêm `?category_id=<id>` và reload danh sách
  - Danh mục đang được chọn sẽ được highlight (active state)
- **Card sản phẩm đa dạng:**
  - Hiển thị ảnh `product.image_url`
  - Hiển thị `product.name`, giá USD (format `$199.99`), category badge
  - Ẩn thông tin chuyên biệt (author, ram...) ở card tổng quan
- Đổi API call JS Add to Cart: `book_id` → `product_id`

### [MODIFY] [book_detail.html](file:///c:/bookstore-micro05/api_gateway/app/templates/book_detail.html) → đổi tên thành `product_detail.html`
**Thay đổi:**
- Đổi tên file → `product_detail.html`
- Hiển thị `product.name` (thay `book.title`), `product.description`
- **Hiển thị Attributes linh hoạt theo loại sản phẩm (JSONB rendering):**
  ```
  Book:    Author, Publisher, Pages, Format, Language
  Laptop:  CPU, RAM, Storage, GPU, OS, Battery
  Mobile:  Brand, RAM, Storage, Camera, Battery
  Shoes:   Brand, Size, Color, Material
  ...
  ```
  Dùng template loop để render: `{% for key, value in product.attributes.items %}`
- Đổi `book_id` → `product_id` trong nút "Add to Cart"

### [MODIFY] [cart.html](file:///c:/bookstore-micro05/api_gateway/app/templates/cart.html)
- Đổi key `item.book_id` → `item.product_id`
- Đổi `item.title` → `item.name`
- Thêm hiển thị category badge bên cạnh tên sản phẩm trong giỏ hàng

### [MODIFY] [staff_dashboard.html](file:///c:/bookstore-micro05/api_gateway/app/templates/staff_dashboard.html)
- Thay tiêu đề "Quản lý Sách" → "Quản lý Sản phẩm"
- Cập nhật form "Thêm sản phẩm": các field `name`, `description`, `price`, `stock`, `image_url`, `category` (dropdown 11 loại), `attributes` (textarea JSON)
- Cập nhật bảng danh sách: hiển thị đúng field `name`, `category`, `price` (USD)
- Thêm cột "Loại" (Book / Laptop / ...) trong bảng quản lý

### [MODIFY] [search.html](file:///c:/bookstore-micro05/api_gateway/app/templates/search.html)
- Đổi field `book.title` → `product.name`
- **Tìm kiếm xuyên suốt tất cả 11 loại sản phẩm theo tên:**
  - Ô tìm kiếm gửi query `?q=<từ khóa>` → Catalog Service tìm trong MongoDB theo field `name` và `description`
  - Kết quả trả về hỗn hợp (Laptop, Book, Shoes... tùy từ khóa người dùng)
  - Cần cập nhật MongoDB text index trong `catalog-service` để index field `name` (thay `title`)
- **Thêm bộ lọc Category** vào sidebar để thu hẹp kết quả sau khi tìm 
- Hiển thị **category badge** trên mỗi kết quả tìm kiếm để phân biệt loại hàng

---

## Thứ tự thực hiện (tránh phụ thuộc vòng tròn)

```
1. catalog-service/views.py + urls.py            → Fix endpoint Sync trước
2. product-service/.../product_model.py          → Sửa URL sync sang đúng endpoint mới
3. cart-service/models.py                        → Đổi book_id → product_id + migrate
4. cart-service/views.py                         → Đổi URL + logic validate
5. api_gateway/views/books.py → [XÓA]           → Thay bằng products.py
6. api_gateway/views/products.py → [TẠO MỚI]   → ProductListView, ProductDetailView...
7. api_gateway/views/cart.py                     → Đổi URL + mapping key
8. api_gateway/views/staff.py                    → Đổi URL service
9. api_gateway/urls.py                           → Đổi import + routes
10. Templates HTML                               → Đổi tên field
```

## Verification Plan

### Automated
- `docker-compose restart product-service catalog-service cart-service` sau mỗi nhóm thay đổi
- `docker-compose logs --tail=20 <service>` kiểm tra không có lỗi import/startup

### Manual
- Test `GET /` → Hiển thị danh sách 110 sản phẩm (không phải sách)
- Test trang chi tiết sản phẩm `/products/<id>/`
- Thêm vào giỏ hàng → Kiểm tra Cart hiển thị đúng tên sản phẩm
- Đăng nhập Staff → Quản lý sản phẩm hoạt động
