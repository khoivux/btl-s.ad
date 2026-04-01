import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .base import BaseProxyView, StaffRequiredMixin

STAFF_SERVICE_URL = "http://staff-service:8000"
BOOK_SERVICE_URL = "http://book-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"

class StaffLoginView(BaseProxyView):
    service_url = STAFF_SERVICE_URL

    def get(self, request):
        return render(request, "staff_login.html")

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        payload = {"username": username, "password": password}
        
        r = self.proxy_request(request, "staff/login/", method="POST", payload=payload)
        
        if r and r.status_code == 200:
            data = r.json()
            request.session['staff_id'] = data['id']
            request.session['staff_name'] = data['username']
            return redirect('staff_dashboard')
        elif r:
            return render(request, "staff_login.html", {"error": "Invalid credentials"})
        else:
            return render(request, "staff_login.html", {"error": "Service Unavailable"})


class StaffDashboardView(StaffRequiredMixin, BaseProxyView):
    service_url = BOOK_SERVICE_URL

    def get(self, request):
        page = request.GET.get('page', 1)
        page_size = 12
        
        r = self.proxy_request(request, f"books/?page={page}&page_size={page_size}", method="GET")
        data = r.json() if r and r.status_code == 200 else {"results": [], "total": 0}
        
        books = data.get('results', [])
        total = data.get('total', 0)
        
        # Calculate pagination
        import math
        total_pages = math.ceil(total / page_size)
        current_page = int(page)
        
        cat_r = requests.get(f"{BOOK_SERVICE_URL}/categories/")
        categories = cat_r.json() if cat_r and cat_r.status_code == 200 else []
        
        return render(request, "staff_dashboard.html", {
            "books": books,
            "total_books": total,
            "current_page": current_page,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "categories": categories,
            "staff_name": request.session.get('staff_name')
        })


class StaffLogoutView(BaseProxyView):
    def get(self, request):
        print(f"[StaffLogoutView] Staff {request.session.get('staff_name')} logged out")
        request.session.pop('staff_id', None)
        request.session.pop('staff_name', None)
        return redirect('staff_login')


@method_decorator(csrf_exempt, name='dispatch')
class StaffBookAddView(StaffRequiredMixin, BaseProxyView):
    service_url = STAFF_SERVICE_URL

    def post(self, request):
        payload = {
            "title": request.POST.get('title'),
            "author": request.POST.get('author'),
            "price": request.POST.get('price'),
            "stock": request.POST.get('stock', 0),
        }
        category_id = request.POST.get('category')
        if category_id:
            payload['category'] = category_id
            
        r = self.proxy_request(request, "staff/books/", method="POST", payload=payload)
        
        if r and r.status_code in (200, 201):
            return redirect('staff_dashboard')
        elif r:
            return render(request, "staff_dashboard.html", {"error": r.json().get('error', 'Failed to add book')})
        else:
            return render(request, "staff_dashboard.html", {"error": "Service Unavailable"})

@method_decorator(csrf_exempt, name='dispatch')
class StaffCategoryAddView(StaffRequiredMixin, BaseProxyView):
    service_url = BOOK_SERVICE_URL

    def post(self, request):
        payload = {
            "name": request.POST.get('name'),
            "description": request.POST.get('description', ''),
        }
        r = self.proxy_request(request, "categories/", method="POST", payload=payload)
        
        if r and r.status_code in (200, 201):
            return redirect('staff_dashboard')
        elif r:
            return render(request, "staff_dashboard.html", {"error": r.json().get('name', 'Failed to add category')})
        else:
            return render(request, "staff_dashboard.html", {"error": "Service Unavailable"})

@method_decorator(csrf_exempt, name='dispatch')
class StaffCategoryModifyView(StaffRequiredMixin, BaseProxyView):
    service_url = BOOK_SERVICE_URL

    def put(self, request, pk):
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, f"categories/{pk}/", method="PUT", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    def delete(self, request, pk):
        r = self.proxy_request(request, f"categories/{pk}/", method="DELETE")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        if r.status_code in (200, 204):
            return JsonResponse({'status': 'deleted'})
        return JsonResponse({'error': 'Failed to delete'}, status=r.status_code)


@method_decorator(csrf_exempt, name='dispatch')
class StaffBookModifyView(StaffRequiredMixin, BaseProxyView):
    service_url = STAFF_SERVICE_URL

    def put(self, request, pk):
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, f"staff/books/{pk}/", method="PUT", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    def delete(self, request, pk):
        r = self.proxy_request(request, f"staff/books/{pk}/", method="DELETE")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        if r.status_code in (200, 204):
            return JsonResponse({'status': 'deleted'})
        return JsonResponse({'error': 'Failed to delete'}, status=r.status_code)


@method_decorator(csrf_exempt, name='dispatch')
class StaffVoucherListCreateView(StaffRequiredMixin, BaseProxyView):
    service_url = ORDER_SERVICE_URL

    def get(self, request):
        r = self.proxy_request(request, "staff/vouchers/", method="GET")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse(r.json(), safe=False, status=r.status_code)

    def post(self, request):
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, "staff/vouchers/", method="POST", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class StaffVoucherDetailView(StaffRequiredMixin, BaseProxyView):
    service_url = ORDER_SERVICE_URL

    def get(self, request, pk):
        r = self.proxy_request(request, f"staff/vouchers/{pk}/", method="GET")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse(r.json(), status=r.status_code)

    def put(self, request, pk):
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, f"staff/vouchers/{pk}/", method="PUT", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    def delete(self, request, pk):
        r = self.proxy_request(request, f"staff/vouchers/{pk}/", method="DELETE")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        if r.status_code == 204:
            return JsonResponse({'status': 'deleted'}, status=200)
        return JsonResponse(r.json(), status=r.status_code)

@method_decorator(csrf_exempt, name='dispatch')
class StaffOrderManageView(StaffRequiredMixin, BaseProxyView):
    service_url = ORDER_SERVICE_URL

    def get(self, request, pk=None):
        if pk:
            r = self.proxy_request(request, f"orders/{pk}/", method="GET")
        else:
            r = self.proxy_request(request, "orders/", method="GET")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse(r.json(), safe=False, status=r.status_code)

    def patch(self, request, pk):
        try:
            data = json.loads(request.body)
            # Backend service still used different endpoint structure, so we keep the proxy paths
            r = self.proxy_request(request, f"orders/{pk}/status/", method="PATCH", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    def delete(self, request, pk):
        r = self.proxy_request(request, f"orders/{pk}/delete/", method="DELETE")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        if r.status_code in (200, 204):
            return JsonResponse({'status': 'deleted'})
        return JsonResponse({'error': 'Failed to delete order'}, status=r.status_code)


