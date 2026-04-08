# 🤖 Tài liệu Hệ thống AI Behavioral Recommender - MicroBook (Version 2025)

Tài liệu này định nghĩa kiến trúc và vận hành của bộ não AI cá nhân hóa cao cấp, kết hợp giữa **Deep Learning (PyTorch)**, **Vector Database** và **RAG Engine (Gemini)**.

---

## 🏗️ 1. Cấu trúc Kiến trúc (Advanced 3-Layer Architecture)

Hệ thống được quy hoạch thành 3 phân vùng chức năng chuyên biệt để đảm bảo sự ổn định và mở rộng:

- **`app/ai_core/` (Lãnh địa Bộ não)**: Chứa mô hình Neural Network (`behavior_trainer.py`), trọng số mô hình (`.pth`) và tập dữ liệu huấn luyện (`.csv`).
- **`app/agents/` (Đại sứ Trí tuệ)**: Chứa Động cơ RAG (`rag_consultant.py`), nơi Gemini LLM thực hiện tư vấn dựa trên tri thức được truy xuất.
- **`app/services/` (Động cơ Vận hành)**: 
    - `recom_service.py`: Điều phối luồng gợi ý cho API và Chatbot.
    - `data_processing.py`: Nhà máy trích xuất và chuẩn hóa dữ liệu 13 chiều từ các Microservices.

---

## 🧠 2. Kỹ nghệ Dữ liệu 13 Chiều (13-Dimensional User Context)

AI không chỉ nhìn vào ID người dùng, nó thấu hiểu khách hàng qua 13 tính năng sinh học (Biographical Features) được tính toán thời gian thực:

| Feature Group | Chi tiết Tri thức |
| :--- | :--- |
| **Behavioral** | Chấm điểm tương tác: Mua hàng (4.0), Giỏ hàng (2.0), Đánh giá (1.0-5.0). |
| **Spending** | Tổng chi tiêu (Spend) được chuẩn hóa qua Log-scale để nắm bắt phân khúc khách hàng. |
| **Recency** | Độ mới của đơn hàng cuối cùng (Days ago) để đề xuất đúng thời điểm. |
| **Frequency** | Tần suất mua sắm để nhận diện khách hàng trung thành. |
| **Interaction** | Số lượng Review và Sản phẩm trong giỏ hàng để đo lường mức độ quan tâm. |

---

## 🚀 3. Động cơ Neural & RAG (Neural Batch Inference)

Chúng ta sử dụng kiến trúc **Two-Tower** với khả năng **Vectorized Batch Scoring**:

1. **Neural Ranking**: Toàn bộ kho sách được nạp vào bộ nhớ đệm (Cache) và chấm điểm đồng loạt qua bộ não Tensor PyTorch (Tốc độ < 0.5s).
2. **RAG Logic**: 
    - **Retrieve**: Lấy ra Top 20 cuốn sách có điểm số Neural cao nhất kèm theo mô tả (Description).
    - **Augment**: Nhồi tri thức thực tế của sách vào Prompt của Gemini.
    - **Generate**: Gemini viết lời tư vấn dựa trên **Sự thật của sách** thay vì khen ngợi sáo rỗng.

---

## 🗣️ 4. Tiêu chuẩn Tư vấn "Tâm giao" (Humanization Rules)

Hệ thống tuân thủ nghiêm ngặt 3 quy tắc "Vàng" khi trò chuyện:

1. **Cấm thuật ngữ (The Ban)**: Tuyệt đối không dùng: Match, Score, AI, Hệ thống, Điểm số, Lọc ra.
2. **Súc tích & Gọn gàng**: Lời chào không quá 1 câu. Đi thẳng vào giá trị của sách.
3. **Mô tả Thực dụng**: Giải thích lợi ích sách dựa trên nội dung mô tả của sản phẩm (Ví dụ: "Sách giúp bạn làm chủ Cloud...").

---

## 🏁 5. Câu lệnh Quản trị & Bảo trì

- **Xuất Dữ liệu Behavioral**: 
  `docker-compose exec recommender-ai-service python manage.py export_behavior`
- **Huấn luyện lại Bộ não AI**: 
  `docker-compose exec recommender-ai-service python manage.py train_behavior`
- **Kiểm tra Sức khỏe AI**:
  Theo dõi tệp `app/ai_core/behavior_model.pth`.

---

## 🌐 6. Mạng lưới Kết nối API (API Connectivity Map)

Hệ thống AI đóng vai trò là "Trung tâm trung chuyển tri thức", kết nối với các Microservices khác qua mạng lưới RESTful API:

### 📥 6.1 Các API tiêu thụ (AI Consumes)
AI "lắng nghe" dữ liệu 13 chiều từ các nguồn sau để xây dựng bối cảnh:

| Service | Endpoint | Mục đích |
| :--- | :--- | :--- |
| **Book Service** | `/books/` | Lấy danh sách Candidate và Mô tả sách cho RAG. |
| **Order Service** | `/orders/` | Lấy lịch sử chi tiêu, tần suất và độ mới (Recency). |
| **Customer Service** | `/customers/` | Lấy hạng thẻ (Loyalty) và tích điểm. |
| **Cart Service** | `/carts/` | Lấy các sản phẩm đang được quan tâm thời gian thực. |
| **Review Service** | `/reviews/` | Lấy cảm xúc và phản hồi của người dùng. |

### 📤 6.2 Các API cung cấp (AI Provides)
AI cung cấp trí tuệ cho Frontend qua các cổng sau:

| Title | Method & Endpoint | Chức năng |
| :--- | :--- | :--- |
| **AI Recommendation** | `GET /api/recommendations/` | Trả về danh sách Top 10 sách xếp hạng theo Neural Brain. |
| **RAG Consultant** | `POST /api/chat/` | Chat tư vấn súc tích, cá nhân hóa (Streaming response). |
| **Chat History** | `GET /api/chat/history/` | Truy xuất lịch sử trò chuyện để Gemini nắm bắt bối cảnh. |

---
*Tài liệu được bảo trì bởi Antigravity AI Consultant.*
