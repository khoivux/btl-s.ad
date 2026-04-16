from django.shortcuts import render, redirect
from django.http import JsonResponse
import requests
import json
from .base import BaseProxyView, CustomerRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

PRODUCT_SERVICE_URL = "http://product-service:8000"
CATALOG_SERVICE_URL = "http://catalog-service:8000"
COMMENT_RATE_SERVICE_URL = "http://comment-rate-service:8006"
ORDER_SERVICE_URL = "http://order-service:8000"
RECOMMENDER_SERVICE_URL = "http://recommender-ai-service:8000"


class ProductListView(BaseProxyView):
    service_url = CATALOG_SERVICE_URL

    def get(self, request):
        page = request.GET.get('page', 1)
        page_size = 12

        endpoint = f"products/?page={page}&page_size={page_size}"
        r = self.proxy_request(request, endpoint, method="GET")

        data = r.json() if r and r.status_code == 200 else {"results": [], "total": 0}
        products = data.get('results', [])
        total = data.get('total', 0)

        import math
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        current_page = int(page)

        # Fetch categories from product-service
        cat_r = requests.get(f"{PRODUCT_SERVICE_URL}/products/categories/", timeout=5)
        categories = cat_r.json() if cat_r and cat_r.status_code == 200 else []

        # Personalized Recommendations
        recommended_products = []
        customer_id = request.session.get('customer_id')
        if customer_id:
            try:
                recom_r = requests.get(f"{RECOMMENDER_SERVICE_URL}/api/recommendations/{customer_id}/", timeout=5)
                if recom_r.status_code == 200:
                    recommended_products = recom_r.json().get('recommendations', [])
            except Exception as e:
                print(f"[GATEWAY] Recommender Error: {e}")

        context = {
            "books": products,  # Keep key as "books" for template compat
            "products": products,
            "total_books": total,
            "current_page": current_page,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "categories": categories,
            "selected_category": request.GET.get('category_id', ''),
            "recommended_books": recommended_products,
        }
        if 'customer_id' in request.session:
            context['customer_id'] = request.session.get('customer_id')
            context['customer_name'] = request.session.get('customer_name')
        return render(request, "products.html", context)


class ProductSearchView(BaseProxyView):
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
        products = data.get('results', [])
        total = data.get('total', 0)

        import math
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        current_page = int(page)

        cat_r = requests.get(f"{PRODUCT_SERVICE_URL}/products/categories/", timeout=5)
        categories = cat_r.json() if cat_r and cat_r.status_code == 200 else []

        context = {
            "books": products,
            "products": products,
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
            "categories": categories,
        }
        if 'customer_id' in request.session:
            customer_id = request.session.get('customer_id')
            context['customer_id'] = customer_id
            context['customer_name'] = request.session.get('customer_name')
            if q:
                try:
                    requests.post(
                        f"http://customer-service:8000/customers/{customer_id}/search-history/",
                        json={'query': q},
                        timeout=2
                    )
                except Exception:
                    pass

        return render(request, "search.html", context)


class ProductDetailView(BaseProxyView):
    service_url = CATALOG_SERVICE_URL

    def get(self, request, product_id):
        r = self.proxy_request(request, f"products/{product_id}/", method="GET")
        if not r or r.status_code == 404:
            return render(request, "404.html", status=404)
        if r.status_code != 200:
            return redirect('product_list')

        product = r.json()

        # Reviews
        reviews_data = {'avg_rating': 0, 'total_reviews': 0, 'reviews': []}
        try:
            rr = requests.get(f"{COMMENT_RATE_SERVICE_URL}/reviews/{product_id}/", timeout=5)
            if rr.status_code == 200:
                reviews_data = rr.json()
        except Exception as e:
            print(f"[{self.__class__.__name__}] Reviews Exception: {e}")

        # Purchase check
        has_purchased = False
        customer_id = request.session.get('customer_id')
        if customer_id:
            try:
                cr = requests.get(
                    f"{ORDER_SERVICE_URL}/api/check-purchase/?customer_id={customer_id}&product_id={product_id}",
                    timeout=5
                )
                if cr.status_code == 200:
                    has_purchased = cr.json().get('has_purchased', False)
            except Exception:
                pass

            # Log interaction
            try:
                requests.post(
                    f"http://customer-service:8000/customers/{customer_id}/interaction-logs/",
                    json={'product_id': product_id, 'action_type': 'VIEW_PRODUCT'},
                    timeout=2
                )
            except Exception:
                pass

        context = {
            "book": product,      # Keep "book" key for template compat
            "product": product,
            "reviews_data": reviews_data,
            "has_purchased": has_purchased,
            "customer_id": customer_id,
            "customer_name": request.session.get('customer_name'),
        }
        return render(request, "product_detail.html", context)


@method_decorator(csrf_exempt, name='dispatch')
class ProductReviewSubmitView(CustomerRequiredMixin, BaseProxyView):
    service_url = COMMENT_RATE_SERVICE_URL

    def post(self, request, product_id):
        try:
            data = json.loads(request.body)
            payload = {
                'customer_id': request.session.get('customer_id'),
                'product_id': product_id,
                'rating': data.get('rating'),
                'comment': data.get('comment', ''),
                'customer_name': request.session.get('customer_name', 'User')
            }
            r = self.proxy_request(request, "reviews/", method="POST", payload=payload)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# Backward compat aliases
BookListView = ProductListView
BookSearchView = ProductSearchView
BookDetailView = ProductDetailView
BookReviewSubmitView = ProductReviewSubmitView
