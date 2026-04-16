import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
import requests
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .base import BaseProxyView, CustomerRequiredMixin

CART_SERVICE_URL = "http://cart-service:8000"
PRODUCT_SERVICE_URL = "http://product-service:8000"
ORDER_SERVICE_URL = "http://order-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"

class CheckoutPageView(CustomerRequiredMixin, BaseProxyView):
    def get(self, request):
        customer_id = request.session['customer_id']
        cart_items = []
        total = 0

        # Fetch cart items
        try:
            self.service_url = CART_SERVICE_URL
            r = self.proxy_request(request, f"carts/{customer_id}/", method="GET")
            raw_items = r.json() if r and r.status_code == 200 else []
            
            for item in raw_items:
                self.service_url = PRODUCT_SERVICE_URL
                prod_r = self.proxy_request(request, f"products/{item['product_id']}/", method="GET")
                product = prod_r.json() if prod_r and prod_r.status_code == 200 else {}
                
                subtotal = float(product.get('price', 0)) * item['quantity']
                total += subtotal
                cart_items.append({
                    'product_id': item['product_id'],
                    'name': product.get('name', ''),
                    'category_name': product.get('category_name', ''),
                    'image_url': product.get('image_url', ''),
                    'price': product.get('price', 0),
                    'quantity': item['quantity'],
                    'subtotal': round(subtotal, 2),
                })
        except Exception as e:
            print(f"[{self.__class__.__name__}] cart/book error: {e}")

        # Fetch addresses
        addresses = []
        try:
            self.service_url = CUSTOMER_SERVICE_URL
            addr_r = self.proxy_request(request, f"customers/{customer_id}/addresses/", method="GET")
            addresses = addr_r.json() if addr_r and addr_r.status_code == 200 else []
        except Exception: pass

        # Fetch customer details
        customer = {}
        try:
            self.service_url = CUSTOMER_SERVICE_URL
            cust_r = self.proxy_request(request, f"customers/{customer_id}/", method="GET")
            customer = cust_r.json() if cust_r and cust_r.status_code == 200 else {}
        except Exception: pass

        # Fetch shipping methods
        shipping_methods = []
        try:
            self.service_url = SHIP_SERVICE_URL
            ship_m_r = self.proxy_request(request, "api/shipping-methods/", method="GET")
            shipping_methods = ship_m_r.json() if ship_m_r and ship_m_r.status_code == 200 else []
        except Exception: pass

        # Membership logic
        membership_level = None
        if customer:
            wallet = customer.get('wallet')
            if wallet and wallet.get('current_level'):
                membership_level = wallet['current_level']
                discount_pct = membership_level.get('discount_percentage', 0)
                if discount_pct > 0:
                    total -= (total * float(discount_pct)) / 100

        # Fetch valid vouchers
        available_vouchers = []
        try:
            self.service_url = ORDER_SERVICE_URL
            v_r = self.proxy_request(request, "vouchers/", method="GET")
            all_vouchers = v_r.json() if v_r and v_r.status_code == 200 else []
            
            redeemed_codes = []
            cv_r = self.proxy_request(request, f"vouchers/customer/{customer_id}/", method="GET")
            if cv_r and cv_r.status_code == 200:
                redeemed_codes = [cv['voucher_details']['code'] for cv in cv_r.json() if not cv.get('is_used')]
                
            current_level_id = membership_level['id'] if membership_level else None
            
            for v in all_vouchers:
                if not v.get('is_active'): continue
                
                is_valid_public = v.get('is_public') and v.get('point_cost', 0) == 0
                is_redeemed = v.get('code') in redeemed_codes
                level_ok = not v.get('min_points_level_id') or (current_level_id and current_level_id >= v['min_points_level_id'])
                min_spend_ok = total >= float(v.get('min_spend', 0))

                if level_ok and min_spend_ok and (is_valid_public or is_redeemed):
                    available_vouchers.append(v)
        except Exception as e:
            print(f"[{self.__class__.__name__}] vouchers error: {str(e)}")

        return render(request, "checkout.html", {
            "cart_items": cart_items,
            "total": round(total, 2),
            "addresses": addresses,
            "shipping_methods": shipping_methods,
            "customer": customer,
            "membership_level": membership_level,
            "vouchers": available_vouchers,
            "customer_name": request.session.get('customer_name'),
            "customer_id": customer_id,
        })


@method_decorator(csrf_exempt, name='dispatch')
class CheckoutApiView(CustomerRequiredMixin, BaseProxyView):
    service_url = ORDER_SERVICE_URL

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}

        customer_id = request.session['customer_id']
        contact = f"{data.get('contact_name', '')} | {data.get('contact_phone', '')}"
        address_text = data.get('shipping_address', '')
        full_address = f"{contact}\n{address_text}"

        pm = data.get('payment_method')
        if not pm: pm = 'COD'

        payload = {
            'customer_id': customer_id,
            'payment_method': pm.upper(),
            'shipping_address': full_address,
            'shipping_method': data.get('shipping_method', 'standard'),
            'shipping_fee': data.get('shipping_fee', 0),
            'voucher_code': data.get('voucher_code', ''),
        }
        
        r = self.proxy_request(request, "orders/", method="POST", payload=payload)
        
        if r and r.status_code in (200, 201):
            try:
                requests.delete(f"{CART_SERVICE_URL}/carts/{customer_id}/clear/")
            except Exception as e:
                print(f"[{self.__class__.__name__}] clear cart error: {e}")
            return JsonResponse(r.json(), status=r.status_code)
        elif r:
            return JsonResponse(r.json(), status=r.status_code)
        return JsonResponse({'error': 'Order service unavailable'}, status=503)


class OrderHistoryView(CustomerRequiredMixin, BaseProxyView):
    service_url = ORDER_SERVICE_URL

    def get(self, request):
        customer_id = request.session['customer_id']
        page = request.GET.get('page', 1)
        page_size = 10
        
        r = self.proxy_request(request, f"orders/?customer_id={customer_id}&page={page}&page_size={page_size}", method="GET")
        data = r.json() if r and r.status_code == 200 else {"results": [], "total": 0}
        
        orders = data.get('results', [])
        total = data.get('total', 0)
        
        import math
        total_pages = math.ceil(total / page_size)
        current_page = int(page)
        
        return render(request, "order_history.html", {
            "orders": orders,
            "total_orders": total,
            "current_page": current_page,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "customer_name": request.session.get('customer_name'),
        })


class OrderSuccessView(BaseProxyView):
    def get(self, request, order_id):
        return render(request, "order_success.html", {
            "order_id": order_id,
            "customer_name": request.session.get('customer_name'),
        })


class OrderDetailView(CustomerRequiredMixin, BaseProxyView):
    def get(self, request, order_id):
        self.service_url = ORDER_SERVICE_URL
        r = self.proxy_request(request, f"orders/{order_id}/", method="GET")
        order = r.json() if r and r.status_code == 200 else {}

        shipment = {}
        if order.get('id'):
            self.service_url = SHIP_SERVICE_URL
            s_r = self.proxy_request(request, f"shipments/order/{order_id}/", method="GET")
            shipment = s_r.json() if s_r and s_r.status_code == 200 else {}

        return render(request, "order_detail.html", {
            "order": order,
            "shipment": shipment,
            "customer_name": request.session.get('customer_name'),
        })


class OrderTrackingView(CustomerRequiredMixin, BaseProxyView):
    def get(self, request, order_id):
        self.service_url = ORDER_SERVICE_URL
        r = self.proxy_request(request, f"orders/{order_id}/", method="GET")
        order = r.json() if r and r.status_code == 200 else {}

        shipment = {}
        if order.get('id'):
            self.service_url = SHIP_SERVICE_URL
            s_r = self.proxy_request(request, f"shipments/order/{order_id}/", method="GET")
            shipment = s_r.json() if s_r and s_r.status_code == 200 else {}

        return render(request, "order_tracking.html", {
            "order": order,
            "shipment": shipment,
            "customer_name": request.session.get('customer_name'),
            "customer_id": request.session.get('customer_id'),
        })


class OrderDetailApiView(BaseProxyView):
    """API for reusable order detail modal, accessible by customers, staff and shippers."""
    def get(self, request, order_id):
        self.service_url = ORDER_SERVICE_URL
        r = self.proxy_request(request, f"orders/{order_id}/", method="GET")
        if not r or r.status_code != 200:
            return JsonResponse({'error': 'Order not found'}, status=404)
        
        order = r.json()
        
        shipment = {}
        self.service_url = SHIP_SERVICE_URL
        s_r = self.proxy_request(request, f"shipments/order/{order_id}/", method="GET")
        if s_r and s_r.status_code == 200:
            shipment = s_r.json()

        return JsonResponse({
            'order': order,
            'shipment': shipment
        })





@method_decorator(csrf_exempt, name='dispatch')
class OrderActionApiView(CustomerRequiredMixin, BaseProxyView):
    service_url = ORDER_SERVICE_URL

    def post(self, request, order_id, action):
        if action == 'cancel':
            r = self.proxy_request(request, f"orders/{order_id}/cancel/", method="POST")
        elif action == 'delete':
            # Front-end forms use POST for simplicity, Order service expects DELETE for deletion
            r = self.proxy_request(request, f"orders/{order_id}/delete/", method="DELETE")
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
        if not r:
            return JsonResponse({'error': 'Service Unavailable'}, status=503)
        return JsonResponse(r.json(), status=r.status_code)
