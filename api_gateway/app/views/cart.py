import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .base import BaseProxyView, CustomerRequiredMixin

CART_SERVICE_URL = "http://cart-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"

class CartView(CustomerRequiredMixin, BaseProxyView):
    service_url = CART_SERVICE_URL

    def get(self, request, customer_id):
        if str(request.session['customer_id']) != str(customer_id):
            return redirect(f"/carts/{request.session['customer_id']}/")

        r = self.proxy_request(request, f"carts/{customer_id}/", method="GET")
        items = r.json() if r and r.status_code == 200 else []

        try:
            b = requests.get(f"{BOOK_SERVICE_URL}/books/")
            books = b.json() if b.status_code == 200 else []
            book_map = {book['id']: book for book in books}
        except Exception:
            book_map = {}

        total_cart_price = 0
        for item in items:
            book_info = book_map.get(item['book_id'], {})
            item['title'] = book_info.get('title', 'Unknown Book')
            price = float(book_info.get('price', 0))
            item['price'] = f"{price:.2f}"
            item['subtotal'] = price * item['quantity']
            total_cart_price += item['subtotal']

        return render(request, "cart.html", {
            "items": items, 
            "customer_name": request.session.get('customer_name'), 
            "total_cart_price": total_cart_price
        })


@method_decorator(csrf_exempt, name='dispatch')
class AddCartItemView(BaseProxyView):
    service_url = CART_SERVICE_URL

    def post(self, request):
        if 'customer_id' not in request.session:
            return JsonResponse({'error': 'Unauthorized', 'redirect': '/login'}, status=401)
            
        try:
            data = json.loads(request.body)
            payload = {
                "cart": data.get('cart_id') or request.session.get('customer_id'),
                "book_id": data.get('book_id'),
                "quantity": data.get('quantity', 1)
            }
            
            r = self.proxy_request(request, "carts/items/", method="POST", payload=payload)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            
            # Log Interaction
            if r.status_code in (200, 201):
                try:
                    customer_id = request.session.get('customer_id')
                    requests.post(f"http://customer-service:8000/customers/{customer_id}/interaction-logs/", json={
                        'book_id': payload['book_id'],
                        'action_type': 'ADD_TO_CART'
                    })
                except Exception:
                    pass
            
            return JsonResponse(r.json(), status=r.status_code)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class ModifyCartItemView(BaseProxyView):
    service_url = CART_SERVICE_URL

    def put(self, request, item_id):
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, f"carts/items/{item_id}/", method="PUT", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    def delete(self, request, item_id):
        r = self.proxy_request(request, f"carts/items/{item_id}/", method="DELETE")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        if r.status_code in (200, 204):
            return JsonResponse({'status': 'deleted'})
        return JsonResponse({'error': 'Failed to delete'}, status=r.status_code)
