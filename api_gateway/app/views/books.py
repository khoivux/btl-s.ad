from django.shortcuts import render, redirect
from django.http import JsonResponse
import requests
import json
from .base import BaseProxyView, CustomerRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Service URLs
BOOK_SERVICE_URL = "http://book-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8006"
ORDER_SERVICE_URL = "http://order-service:8000"

RECOMMENDER_SERVICE_URL = "http://recommender-ai-service:8000"

class BookListView(BaseProxyView):
    service_url = CATALOG_SERVICE_URL

    def get(self, request):
        page = request.GET.get('page', 1)
        page_size = 12
        
        search_query = request.GET.get('search', '')
        endpoint = f"books/?page={page}&page_size={page_size}"
        r = self.proxy_request(request, endpoint, method="GET")
        
        data = r.json() if r and r.status_code == 200 else {"results": [], "total": 0}
        books = data.get('results', [])
        total = data.get('total', 0)
        
        import math
        total_pages = math.ceil(total / page_size)
        current_page = int(page)
        
        cat_r = requests.get(f"{BOOK_SERVICE_URL}/categories/")
        categories = cat_r.json() if cat_r and cat_r.status_code == 200 else []
        
        # Personalized Recommendations
        recommended_books = []
        customer_id = request.session.get('customer_id')
        if customer_id:
            try:
                # Call AI Recommender Service (Keep this separate from pagination)
                recom_r = requests.get(f"{RECOMMENDER_SERVICE_URL}/api/recommendations/{customer_id}/")
                if recom_r.status_code == 200:
                    recom_data = recom_r.json()
                    recommended_books = recom_data.get('recommendations', [])
            except Exception as e:
                print(f"[GATEWAY] Recommender Error: {e}")

        context = {
            "books": books, 
            "total_books": total,
            "current_page": current_page,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "search": search_query, 
            "categories": categories,
            "recommended_books": recommended_books
        }
        if 'customer_id' in request.session:
            context['customer_id'] = request.session.get('customer_id')
            context['customer_name'] = request.session.get('customer_name')
        return render(request, "books.html", context)



class BookSearchView(BaseProxyView):
    service_url = CATALOG_SERVICE_URL
    
    def get(self, request):
        page = request.GET.get('page', 1)
        page_size = 12
        
        q = request.GET.get('q', '')
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')
        sort = request.GET.get('sort', '')
        category_id = request.GET.get('category_id', '')

        endpoint = f"search/?page={page}&page_size={page_size}"
        r = self.proxy_request(request, endpoint, method="GET")

        data = r.json() if r and r.status_code == 200 else {"results": [], "total": 0}
        books = data.get('results', [])
        total = data.get('total', 0)
        
        import math
        total_pages = math.ceil(total / page_size)
        current_page = int(page)
        
        cat_r = requests.get(f"{BOOK_SERVICE_URL}/categories/")
        categories = cat_r.json() if cat_r and cat_r.status_code == 200 else []

        context = {
            "books": books,
            "total_books": total,
            "current_page": current_page,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "q": q,
            "min_price": min_price,
            "max_price": max_price,
            "sort": sort,
            "category_id": category_id,
            "categories": categories
        }
        if 'customer_id' in request.session:
            customer_id = request.session.get('customer_id')
            context['customer_id'] = customer_id
            context['customer_name'] = request.session.get('customer_name')
            # Log Search History
            if q:
                try:
                    requests.post(f"http://customer-service:8000/customers/{customer_id}/search-history/", json={'query': q})
                except Exception:
                    pass
            
        return render(request, "search.html", context)


class BookDetailView(BaseProxyView):
    service_url = CATALOG_SERVICE_URL

    def get(self, request, book_id):
        # Chi tiết sách - /books/<book_id>/
        # 1. Fetch book details
        r = self.proxy_request(request, f"books/{book_id}/", method="GET")
        if not r or r.status_code == 404:
            return render(request, "404.html", status=404)
        if r.status_code != 200:
            return redirect('book_list')
            
        book = r.json()

        # 2. Fetch reviews
        reviews_data = {'avg_rating': 0, 'total_reviews': 0, 'reviews': []}
        try:
            rr = requests.get(f"{COMMENT_RATE_SERVICE_URL}/reviews/{book_id}/")
            if rr.status_code == 200:
                reviews_data = rr.json()
        except Exception as e:
            print(f"[{self.__class__.__name__}] Reviews Exception: {e}")

        # 3. Check purchase
        has_purchased = False
        customer_id = request.session.get('customer_id')
        if customer_id:
            try:
                cr = requests.get(f"{ORDER_SERVICE_URL}/api/check-purchase/?customer_id={customer_id}&book_id={book_id}")
                if cr.status_code == 200:
                    has_purchased = cr.json().get('has_purchased', False)
            except Exception as e:
                print(f"[{self.__class__.__name__}] CheckPurchase Exception: {e}")

            # Log Book View Interaction
            try:
                requests.post(f"http://customer-service:8000/customers/{customer_id}/interaction-logs/", json={
                    'book_id': book_id,
                    'action_type': 'VIEW_BOOK'
                })
            except Exception:
                pass

        context = {
            "book": book,
            "reviews_data": reviews_data,
            "has_purchased": has_purchased,
            "customer_id": customer_id,
            "customer_name": request.session.get('customer_name')
        }
        return render(request, "book_detail.html", context)


@method_decorator(csrf_exempt, name='dispatch')
class BookReviewSubmitView(CustomerRequiredMixin, BaseProxyView):
    service_url = COMMENT_RATE_SERVICE_URL

    def post(self, request, book_id):
        # Gửi đánh giá sách - /api/books/<book_id>/reviews/
        try:
            data = json.loads(request.body)
            payload = {
                'customer_id': request.session.get('customer_id'),
                'book_id': book_id,
                'rating': data.get('rating'),
                'comment': data.get('comment', ''),
                'customer_name': request.session.get('customer_name', 'User')
            }
            
            r = self.proxy_request(request, "reviews/", method="POST", payload=payload)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
                
            return JsonResponse(r.json(), status=r.status_code)
            
        except Exception as e:
            print(f"[{self.__class__.__name__}] Exception: {e}")
            return JsonResponse({'error': str(e)}, status=500)
