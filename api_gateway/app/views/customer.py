import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .base import BaseProxyView, CustomerRequiredMixin

CUSTOMER_SERVICE_URL = "http://customer-service:8000"

class ProfileView(CustomerRequiredMixin, BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def get(self, request):
        customer_id = request.session['customer_id']
        r = self.proxy_request(request, f"customers/{customer_id}/", method="GET")
        customer_data = r.json() if r and r.status_code == 200 else {}

        return render(request, "profile.html", {
            "customer": customer_data,
            "customer_name": request.session.get('customer_name'),
            "customer_id": customer_id
        })


@method_decorator(csrf_exempt, name='dispatch')
class ProfileApiView(CustomerRequiredMixin, BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def put(self, request):
        return self._handle_update(request)
        
    def post(self, request):
        return self._handle_update(request)
        
    def _handle_update(self, request):
        customer_id = request.session['customer_id']
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, f"customers/{customer_id}/", method="PUT", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
                
            if r.status_code == 200:
                new_data = r.json()
                if 'name' in new_data:
                    request.session['customer_name'] = new_data['name']
            return JsonResponse(r.json(), status=r.status_code)
        except Exception as e:
            print(f"[{self.__class__.__name__}] Exception: {e}")
            return JsonResponse({'error': str(e)}, status=500)


class LoginView(BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        payload = {"email": email, "password": password}
        
        r = self.proxy_request(request, "customers/login/", method="POST", payload=payload)
        
        if r and r.status_code == 200:
            user_data = r.json()
            request.session['customer_id'] = user_data['id']
            request.session['customer_name'] = user_data['name']
            return redirect('book_list')
        elif r:
            return render(request, "login.html", {"error": "Invalid email or password"})
        else:
            return render(request, "login.html", {"error": "Service Unavailable"})


class RegisterView(BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def get(self, request):
        return render(request, "register.html")

    def post(self, request):
        payload = {
            "name": request.POST.get('name'),
            "email": request.POST.get('email'),
            "phone_number": request.POST.get('phone_number', ''),
            "password": request.POST.get('password')
        }
        
        r = self.proxy_request(request, "customers/", method="POST", payload=payload)
        
        if r and r.status_code in (200, 201):
            return redirect('login')
        elif r:
            return render(request, "register.html", {"error": r.json().get('error', 'Registration Failed')})
        else:
            return render(request, "register.html", {"error": "Service Unavailable"})


class LogoutView(BaseProxyView):
    def get(self, request):
        print(f"[LogoutView] Customer {request.session.get('customer_id')} logged out")
        request.session.flush()
        return redirect('book_list')


@method_decorator(csrf_exempt, name='dispatch')
class AddressApiListView(BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def get(self, request, customer_id):
        r = self.proxy_request(request, f"customers/{customer_id}/addresses/", method="GET")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse(r.json(), safe=False)

    def post(self, request, customer_id):
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, f"customers/{customer_id}/addresses/", method="POST", payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AddressApiDetailView(BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def delete(self, request, customer_id, pk):
        r = self.proxy_request(request, f"customers/{customer_id}/addresses/{pk}/", method="DELETE")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse({'status': 'deleted'}, status=204)

    def put(self, request, customer_id, pk):
        return self._handle_update(request, customer_id, pk, method="PUT")

    def patch(self, request, customer_id, pk):
        return self._handle_update(request, customer_id, pk, method="PATCH")

    def _handle_update(self, request, customer_id, pk, method):
        try:
            data = json.loads(request.body)
            r = self.proxy_request(request, f"customers/{customer_id}/addresses/{pk}/", method=method, payload=data)
            if not r:
                return JsonResponse({'error': 'Service Unavailable'}, status=503)
            return JsonResponse(r.json(), status=r.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PointTransactionApiView(CustomerRequiredMixin, BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def get(self, request):
        customer_id = request.session['customer_id']
        page = request.GET.get('page', 1)
        # Use simple string interpolation for params since we only have one
        r = self.proxy_request(request, f"customers/{customer_id}/wallet/transactions/?page={page}", method="GET")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse(r.json(), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class ChatHistoryApiView(CustomerRequiredMixin, BaseProxyView):
    service_url = CUSTOMER_SERVICE_URL

    def get(self, request):
        customer_id = request.session['customer_id']
        r = self.proxy_request(request, f"customers/{customer_id}/chat-messages/", method="GET")
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse(r.json(), safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class ChatConsultantApiView(CustomerRequiredMixin, BaseProxyView):
    service_url = "http://recommender-ai-service:8000"

    def post(self, request):
        customer_id = request.session['customer_id']
        try:
            data = json.loads(request.body)
            # Use streaming requests to proxy the chunks
            r = requests.post(
                f"{self.service_url}/chat/consultant/{customer_id}/",
                json=data,
                stream=True,
                timeout=30
            )
            
            if r.status_code != 200:
                return JsonResponse({'error': 'AI Service Error'}, status=r.status_code)

            def stream_chunks():
                print("[GATEWAY] Starting stream from AI Service...")
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        text = chunk.decode('utf-8')
                        print(f"[GATEWAY] Received chunk: {len(text)} chars")
                        yield text

            response = StreamingHttpResponse(stream_chunks(), content_type='text/plain')
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Accel-Buffering'] = 'no'
            return response
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RecommenderProxyView(BaseProxyView):
    service_url = "http://recommender-ai-service:8000"

    def post(self, request, path):
        return self.proxy_request(request, f"api/{path}", method="POST")

    def get(self, request, path):
        return self.proxy_request(request, f"api/{path}", method="GET")
