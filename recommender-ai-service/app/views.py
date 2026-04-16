import os
import time
import requests
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import StreamingHttpResponse
from django.conf import settings
from .services.recom_service import get_recommendations
from .agents.rag_consultant import consultant_agent
from .ai_core.vector_db import vector_db

# Service URLs
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"

class RecommendationApiView(APIView):
    """
    Standard Personalized recommendations (Phase 0 logic - Weighted).
    """
    def get(self, request, customer_id=None):
        if not customer_id:
            customer_id = request.query_params.get('customer_id')
        try:
            cid = int(customer_id) if customer_id else None
        except (TypeError, ValueError):
            cid = None
        recommendations = get_recommendations(cid)
        return Response({
            'customer_id': cid,
            'recommendations': recommendations,
            'count': len(recommendations)
        })

class ConsultantChatView(APIView):
    """
    AI Chat Consultant with RAG and persistent history.
    """
    def post(self, request, customer_id):
        user_message = request.data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=400)
        
        # 1. Fetch History from customer-service
        try:
            hist_r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/chat-messages/")
            chat_history = hist_r.json() if hist_r.status_code == 200 else []
        except Exception:
            chat_history = []

        # 2. Save User Message
        try:
            requests.post(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/chat-messages/", json={
                'role': 'user', 'content': user_message
            })
        except Exception:
            pass

        # 3. Stream AI Advice
        print(f"\n[STREAM] User #{customer_id}: {user_message}")

        def stream_response_and_save():
            full_advice = ""
            try:
                for chunk in consultant_agent.get_advice_stream(customer_id, user_message, chat_history):
                    full_advice += chunk
                    yield chunk
                
                # 4. Save COMPLETE AI Response after stream ends
                print(f"[STREAM COMPLETE] Saved response to DB")
                requests.post(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/chat-messages/", json={
                    'role': 'assistant', 'content': full_advice
                })
            except Exception as e:
                print(f"[STREAM ERR] {e}")
                yield f"\n[Lỗi hệ thống]: {str(e)}"

        response = StreamingHttpResponse(stream_response_and_save(), content_type='text/plain')
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Accel-Buffering'] = 'no'
        return response

class VectorIndexProductsView(APIView):
    """
    Endpoint to trigger re-indexing of all products into ChromaDB Knowledge Base.
    """
    def post(self, request):
        try:
            # ─── Bước 0: Tẩy não AI (Xóa trí nhớ cũ) ──────────────────────────
            # Đảm bảo 100% dữ liệu cũ, lỗi hoặc rác bị dọn sạch trước khi nạp mới.
            print("[INDEXER] Đang xóa bộ nhớ cũ của ChromaDB...")
            vector_db.clear_all()

            # ─── Bước 1: Thu thập sản phẩm từ Catalog Service ────────────
            # Gọi API sang catalog-service để lấy thông tin chi tiết nhất của mọi sản phẩm.
            print("[INDEXER] Đang gọi Catalog Service lấy 100% sản phẩm...")
            r = requests.get(f"{CATALOG_SERVICE_URL}/products/?limit=1000")
            if r.status_code != 200:
                return Response({'error': 'Không thể kết nối Catalog Service'}, status=500)
            
            data = r.json()
            products = data.get('results', [])
            
            ids, docs, metas = [], [], []
            for p in products:
                # Trích xuất nội dung văn bản để AI "học"
                print(f"[INDEXER] Chuẩn bị dữ liệu cho sản phẩm: {p['name']} (ID: {p['id']})")
                content = (
                    f"Tên sản phẩm: {p['name']}\n"
                    f"Giá bán: {p.get('price', 'Liên hệ')} $\n"
                    f"Danh mục: {p.get('category_name', 'Chung')}\n"
                    f"Mô tả: {p.get('description', '')}\n"
                    f"Thông số: {json.dumps(p.get('attributes', {}))}"
                )
                ids.append(str(p['id']))
                docs.append(content)
                metas.append({
                    "id": p['id'],
                    "title": p['name'],
                    "category": p.get('category_name', 'General'),
                    "price": float(p.get('price', 0))
                })
            
            # ─── Bước 2: Nạp sách vào Vector DB (Chia mẻ mini-batch) ───────────
            # Chia nhỏ 10 cuốn mỗi mẻ nạp để tránh làm Google Gemini "khó chịu" (Rate Limit).
            batch_size = 10
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_docs = docs[i:i + batch_size]
                batch_metas = metas[i:i + batch_size]
                
                print(f"[INDEXER] Đang nạp Mẻ sản phẩm ({i+1}-{i+len(batch_ids)}/{len(ids)}) vào Vector DB...")
                try:
                    vector_db.upsert_products(batch_ids, batch_docs, batch_metas)
                except Exception as e:
                    print(f"[INDEXER] Mẻ nạp bị lỗi, thử lại sau 10 giây: {e}")
                    time.sleep(10) # Long wait if hit limit
                    vector_db.upsert_books(batch_ids, batch_docs, batch_metas)
                
                # Nghỉ 6 giây để ổn định tốc độ nạp (Dành riêng cho hạn mức 100 RPM của Free Tier Google)
                time.sleep(6)

            # ─── Bước 3: Nạp các tệp Kiến thức bổ trợ (Chính sách, Vận chuyển) ───
            # Đọc các file .md trong thư mục kb_docs để AI hiểu về Phí ship, Hạng thành viên...
            kb_ids, kb_docs, kb_metas = [], [], []
            kb_path = os.path.join(settings.BASE_DIR, "app", "kb_docs")
            if os.path.exists(kb_path):
                for filename in os.listdir(kb_path):
                    if filename.endswith(".md") or filename.endswith(".txt"):
                        print(f"[INDEXER] Đang đọc Tài liệu Kiến thức: {filename}")
                        with open(os.path.join(kb_path, filename), "r", encoding="utf-8") as f:
                            content = f.read()
                            kb_ids.append(f"doc_{filename}")
                            kb_docs.append(content)
                            kb_metas.append({"source": filename, "type": "policy_advice"})
            
            if kb_ids:
                print(f"[INDEXER] Đang nạp {len(kb_ids)} tệp kiến thức bổ trợ vào Vector DB...")
                vector_db.upsert_products(kb_ids, kb_docs, kb_metas)

            print("[INDEXER] 🏆 QUY TRÌNH NẠP KIẾN THỨC HOÀN TẤT 100%!")
            return Response({'status': 'Đã hoàn tất nạp 100% kho tri thức sản phẩm và chính sách.'})
        except Exception as e:
            print(f"[INDEXER LỖI] {e}")
            return Response({'error': str(e)}, status=500)
