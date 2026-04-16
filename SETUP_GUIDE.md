# 🚀 Hướng Dẫn Cài Đặt Dự Án MicroStore AI

Tài liệu này hướng dẫn chi tiết các bước để triển khai hệ thống Microservices Bookstore tích hợp Trí tuệ nhân tạo (LSTM & RAG).

---

## 📋 1. Yêu cầu hệ thống
Trước khi bắt đầu, hãy đảm bảo máy tính của bạn đã cài đặt:
*   **Docker & Docker Compose** (Khuyến nghị Docker Desktop trên Windows/Mac)
*   **Git**
*   **Google AI API Key** (Lấy tại [Google AI Studio](https://aistudio.google.com/app/apikey))

---

## 🛠️ 2. Các bước triển khai

### Bước 1: Clone dự án và cấu hình môi trường
Mở Terminal tại thư mục dự án và tạo file môi trường cho AI Service:

1. Di chuyển vào thư mục AI: `cd recommender-ai-service`
2. Tạo file `.env` và thêm key của bạn:
   ```env
   GOOGLE_API_KEY=Cái_Key_AI_Của_Bạn_Tại_Đây
   ```

### Bước 2: Khởi động hệ thống Docker
Hệ thống gồm nhiều dịch vụ (PostgreSQL, Neo4j, Redis, Python Services). Chạy lệnh sau tại thư mục gốc:

```powershell
docker-compose up -d --build
```
*Đợi khoảng 2-5 phút để Docker tải image và khởi động các container.*

---

## 🧠 3. Khởi tạo dữ liệu & Huấn luyện AI (Bắt buộc)
Để AI có thể hoạt động, bạn cần nạp dữ liệu mồi và huấn luyện mô hình theo thứ tự sau:

### 1️⃣ Nạp dữ liệu sản phẩm mẫu
```powershell
# Nạp sản phẩm vào Catalog Service
Invoke-RestMethod -Method Post -Uri "http://localhost:8011/api/catalog/seed-products/"
```

### 2️⃣ Khởi tạo hành vi & Huấn luyện mô hình LSTM
AI cần biết người dùng thường xem gì để gợi ý:
```powershell
# Bước A: Tạo dữ liệu giả lập (260 tương tác)
Invoke-RestMethod -Method Post -Uri "http://localhost:8010/api/recommender/export-behavior/"

# Bước B: Huấn luyện bộ não AI (Chạy 10 Epochs)
Invoke-RestMethod -Method Post -Uri "http://localhost:8010/api/recommender/train-behavior/"
```

### 3️⃣ Nạp tri thức vào Vector Database (RAG)
Để Chatbot có thể tư vấn sản phẩm, bạn cần nạp thông tin vào ChromaDB:
```powershell
# AI sẽ đọc toàn bộ 110 sản phẩm và lưu vào bộ nhớ vector
Invoke-RestMethod -Method Post -Uri "http://localhost:8010/api/recommender/index-kb/"
```

---

## 🌐 4. Truy cập hệ thống
Sau khi hoàn tất các bước trên, bạn có thể trải nghiệm tại:

*   **Trang chủ (Gateway):** [http://localhost:8000](http://localhost:8000)
*   **AI Chat Consultant:** Truy cập trang chi tiết sản phẩm và sử dụng khung Chat bên dưới.
*   **Admin Dashboard:** [http://localhost:8000/admin/](http://localhost:8000/admin/) (Nếu có cấu hình).

---

## 🔍 5. Kiểm tra lỗi (Troubleshooting)
Nếu gặp lỗi "Gián đoạn kỹ thuật", hãy kiểm tra Logs:
```powershell
docker-compose logs --tail=50 recommender-ai-service
```
Đảm bảo rằng `GOOGLE_API_KEY` trong file `.env` vẫn còn hạn sử dụng và không bị Google chặn.

---
**Chúc bạn có những trải nghiệm tuyệt vời với MicroStore AI!** 📚🤖
