import requests
from django.views import View
from django.shortcuts import redirect

class BaseProxyView(View):
    service_url = None

    def proxy_request(self, request, path, method="GET", payload=None):
        url = f"{self.service_url}/{path}"
        headers = {'Content-Type': 'application/json'}
        try:
            if method == "GET":
                response = requests.get(url, params=request.GET, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=payload, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=payload, headers=headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, json=payload, headers=headers, timeout=30)
            else:
                return None
            return response
        except requests.exceptions.RequestException as e:
            print(f"[{self.__class__.__name__}] Proxy Error to {url}: {e}")
            return None

class CustomerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if 'customer_id' not in request.session:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

class StaffRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if 'staff_id' not in request.session:
            return redirect('staff_login')
        return super().dispatch(request, *args, **kwargs)