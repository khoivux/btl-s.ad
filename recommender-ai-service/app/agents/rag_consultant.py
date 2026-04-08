import google.generativeai as genai
from django.conf import settings
from ..ai_core.vector_db import vector_db

# Configure Google SDK directly for maximum stability
genai.configure(api_key=settings.GOOGLE_API_KEY)

class ConsultantAgent:
    def __init__(self):
        # Fallback to the latest available flash model to avoid 0 or strict quotas on older models.
        self.model = genai.GenerativeModel('gemini-flash-latest')

    def get_advice_stream(self, user_id, user_message, chat_history_list=None):
        # 1. Persona and Context
        print(f"[AI-LOG] Fetching behavior context for user {user_id}...")
        
        # 1.1 Fetch real-time customer context from customer-service
        points, level_id = 0, 1
        try:
            from ..ai_core.behavior_trainer import behavior_trainer
            import requests # Ensure requests is imported
            
            cust_r = requests.get(f"http://customer-service:8000/customers/{user_id}/", timeout=1)
            if cust_r.status_code == 200:
                c_data = cust_r.json()
                wallet = c_data.get('wallet', {})
                points = wallet.get('usable_points', 0)
                level_id = wallet.get('current_level', {}).get('id', 1)
                print(f"[AI-LOG] User {user_id} detected: Points={points}, Level={level_id}")
        except Exception as e:
            print(f"[AI-LOG] Behavioral context failed: {e}")

        persona = f"Khách hàng số #{user_id} (Hạng thẻ {level_id}, tích lũy {points} điểm). Người quan tâm đến Bookstore."

        # R. Retrieval: Optimized to rank based on both Vector Search and Behavioral Score
        kb_results = vector_db.query(user_message, n_results=150)
        docs = kb_results.get('documents', [[]])[0]
        
        try:
            from .model_behavior import behavior_trainer
            
            # --- NEURAL RANKING SESSION (13-dim Context Aware) ---
            # Fetch 20 books WITH DESCRIPTIONS for deep reasoning
            print(f"[AI-LOG] 🧠 Identifying Neural Gems with Metadata for User {user_id}...")
            ai_recs = behavior_trainer.get_recommendations(user_id, top_k=20)
            
            recom_context = ""
            if ai_recs:
                recom_context = "\n".join([
                    f"- {r['title']} (Loại: {r['category']}, Tác giả: {r['author']}, Giá: {r['price']}đ, Match: {r['score']}đ)\n  MÔ TẢ: {r['description'][:200]}..." 
                    for r in ai_recs
                ])
                print(f"[AI-LOG] AI Pool of 20 books (with descriptions) ready.")
            
            kb_context = f"DỰA TRÊN HÀNH VI CỦA KHÁCH (AI RECOMMENDS):\n{recom_context}\n\nKHO SÁCH LIÊN QUAN (VECTOR DB):\n" + "\n".join(docs[:5])
        except Exception as e:
            print(f"[AI-LOG] Failed behavioral ranking: {e}")
            kb_context = "\n".join(docs[:5])

        # 3. History
        history_text = ""
        if isinstance(chat_history_list, list):
            for m in chat_history_list:
                role = "Khách" if m.get('role') == 'user' else "AI"
                history_text += f"{role}: {m.get('content')}\n"

        # 4. Prompt
        print(f"[AI-LOG] Generating natural prompt for user {user_id}.")
        system_prompt = f"""Bạn là một chuyên gia tư vấn sách 'Tâm giao' của hiệu sách MicroBook-AI với hơn 20 năm kinh nghiệm thấu hiểu độc giả.

NHIỆM VỤ CỦA BẠN:
1. Trò chuyện như một NGƯỜI BẠN đang kể về những cuốn sách hay, KHÔNG PHẢI một cỗ máy đang báo cáo kết quả.
2. TUYỆT ĐỐI CẤM (BLACKLIST): 'Điểm tương thích', 'Match', 'Lọc ra', 'Tầm giá', 'Kết quả', 'Đề xuất dựa trên...', 'Hệ thống đã chọn'.
3. PHONG CÁCH TƯ VẤN:
   - Hãy nói một cách tự nhiên nhất: 'Tôi vừa tìm thấy mấy cuốn này hay lắm...', 'Có 3 cuốn này tôi tin bạn sẽ rất thích...', 'Với khoảng $7, bạn có thể chọn ngay...'.
   - Giải thích lý do dựa trên GIÁ TRỊ CỐT LÕI của sách (ví dụ: 'Cuốn này giúp bạn nắm vững Cloud vì nó có nhiều bài tập thực tế').
   - Lời chào ngắn gọn (tối đa 1 câu). Không rườm rà về việc AI đang làm gì.

QUY TẮC PHỤC VỤ (BÍ MẬT):
- Luôn ưu tiên 3 cuốn đầu trong danh sách 'AI RECOMMENDS' trừ khi khách yêu cầu số lượng K khác.
- Chỉ tư vấn những cuốn có trong danh sách được cung cấp.
- Nếu không thấy sách phù hợp với yêu cầu cụ thể, hãy thành thật xin lỗi và gợi ý cuốn gần nhất.

DỮ LIỆU BỐI CẢNH (CHỈ DÙNG ĐỂ THẤU HIỂU, KHÔNG ĐƯỢC CHÉP LẠI):
---
HỒ SƠ ĐỘC GIẢ: {persona} (Ví dụ: 242 điểm = Khách hàng thân thiết).
DANH SÁCH GỢI Ý NGẦM: {kb_context}
---

LỊCH SỬ TRÒ CHUYỆN:
{history_text}

HÃY BẮT ĐẦU TƯ VẤN NGAY (Bằng Tiếng Việt, ấm áp và lôi cuốn):
"""
        full_prompt = f"{system_prompt}\n\nKhách: {user_message}\nAI:"
        
        # 5. Stream output word by word for 'typing' effect
        try:
            response = self.model.generate_content(full_prompt, stream=True)
            import time
            for chunk in response:
                if chunk.text:
                    # Force word splitting to avoid one-shot large chunks
                    print(f"[AI-LOG] Chunk received: {chunk.text[:20]}...")
                    words = chunk.text.split(' ')
                    for i, word in enumerate(words):
                        space = ' ' if i < len(words) - 1 else ''
                        yield word + space
                        time.sleep(0.015) # Microscopic sleep for human-like typing
        except Exception as e:
            print(f"[STREAM ERROR] Fallback triggered due to: {e}")
            # ─── Chế độ dự phòng: Tìm kiếm tri thức thô khi Gemini lỗi ─────────
            yield "Chào bạn! Thành thật xin lỗi vì hệ thống đang gặp chút gián đoạn kỹ thuật nhỏ và chưa thể phản hồi linh hoạt nhất ngay lúc này. Tuy nhiên, tôi đã trích xuất nhanh một số thông tin khớp nhất từ kho tri thức của Bookstore, mời bạn xem qua nhé:\n\n"
            
            # Hiển thị 10 đoạn kiến thức vụn khớp nhất (thô)
            fallback_docs = docs[:10] if docs else []
            if fallback_docs:
                for i, doc in enumerate(fallback_docs):
                    yield f"📍 [Thông tin tham khảo {i+1}]:\n{doc}\n\n"
            else:
                yield "Rất tiếc, hiện tại tôi cũng không tìm thấy đoạn thông tin tự động nào phù hợp. Vui lòng thử lại sau ít phút hoặc nhắn tin cho nhân viên hỗ trợ nhé!"

    def get_advice(self, user_id, user_message, chat_history_list=None):
        # Keep existing non-streaming for legacy/internal use
        try:
            full_advice = ""
            for chunk in self.get_advice_stream(user_id, user_message, chat_history_list):
                full_advice += chunk
            return full_advice
        except Exception as e:
            print(f"[CHAT ERROR] {e}")
            return "Tôi xin lỗi, 'bộ não' AI hiện đang có vấn đề."

# Singleton
consultant_agent = ConsultantAgent()
