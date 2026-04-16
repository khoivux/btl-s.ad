from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order, OrderItem, Voucher, CustomerVoucher
from .serializers import OrderSerializer, VoucherSerializer, CustomerVoucherSerializer
import requests
import decimal
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import django.utils.timezone

CART_SERVICE_URL = "http://cart-service:8000"
PRODUCT_SERVICE_URL = "http://product-service:8000"
PAY_SERVICE_URL  = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"
CUSTOMER_SERVICE_URL = "http://customer-service:8000"

def _log(tag, r):
    print(f"[order-service][{tag}] {r.request.method} {r.url} → {r.status_code}")

def _add_status_log(order, status, notes=""):
    from .models import OrderStatusLog
    OrderStatusLog.objects.create(order=order, status=status, notes=notes)

class OrderListCreate(APIView):
    """
    POST /orders/  → Checkout: Create order, process payment, create shipment.
    GET  /orders/?customer_id=<id> → Order history for a customer.
    """
    def post(self, request):
        customer_id = request.data.get('customer_id')
        payment_method = request.data.get('payment_method', 'COD')
        shipping_address = request.data.get('shipping_address', '')
        shipping_method = request.data.get('shipping_method', 'standard')
        shipping_fee = decimal.Decimal(str(request.data.get('shipping_fee', 0)))

        if not customer_id:
            return Response({'error': 'customer_id is required'}, status=400)

        # ── Step 1: Fetch cart items ───────────────────────────────────────────
        print(f"[order-service] Step 1: Fetching cart for customer {customer_id}")
        try:
            cart_resp = requests.get(f"{CART_SERVICE_URL}/carts/{customer_id}/")
            _log("fetch_cart", cart_resp)
            cart_items = cart_resp.json()
        except Exception as e:
            return Response({'error': f'cart-service unavailable: {e}'}, status=503)

        if not cart_items:
            return Response({'error': 'Cart is empty'}, status=400)

        # ── Step 2: Fetch product details & snapshot prices ───────────────────────
        print(f"[order-service] Step 2: Fetching product prices (snapshot)")
        order_items_data = []
        total_amount = decimal.Decimal('0')

        for item in cart_items:
            product_id = item['product_id']
            quantity = item['quantity']
            try:
                product_resp = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}/")
                _log(f"fetch_product_{product_id}", product_resp)
                product = product_resp.json()
                unit_price = decimal.Decimal(str(product['price']))
                total_amount += unit_price * quantity
                order_items_data.append({
                    'product_id': product_id,
                    'product_name': product.get('name', ''),
                    'item_image_url': product.get('image_url', ''),
                    'quantity': quantity,
                    'unit_price': unit_price,
                })
            except Exception as e:
                return Response({'error': f'product-service error for product {product_id}: {e}'}, status=503)

        # ── Step 2.5: Loyalty & Discounts ────────────────────────────────────
        print(f"[order-service] Step 2.5: Checking loyalty for customer {customer_id}")
        membership_discount = decimal.Decimal('0')
        points_to_generate = int(total_amount)  # 1$ = 1 pt
        wallet = None
        
        try:
            cust_resp = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/")
            if cust_resp.status_code == 200:
                customer_data = cust_resp.json()
                wallet = customer_data.get('wallet')
                if wallet and wallet.get('current_level'):
                    tier_discount = wallet['current_level']['discount_percentage']
                    if tier_discount > 0:
                        membership_discount = (total_amount * decimal.Decimal(str(tier_discount))) / 100
                        print(f"[order-service] Tier discount applied: {tier_discount}% (-{membership_discount})")
        except Exception as e:
            print(f"[order-service] Could not fetch loyalty info: {e}")

        # ── Step 2.6: Voucher Handling ─────────────────────────────────────────
        voucher_discount = decimal.Decimal('0')
        voucher_code = request.data.get('voucher_code')
        if not voucher_code:
            voucher_code = ''
        if voucher_code:
            try:
                voucher = Voucher.objects.filter(code=voucher_code, is_active=True).first()
                if not voucher:
                    return Response({'error': 'Invalid or expired voucher code.'}, status=400)

                # Check if it's a public voucher OR if the customer owns it
                is_available = False
                ownership = CustomerVoucher.objects.filter(customer_id=customer_id, voucher=voucher, is_used=False).first()

                # ONLY allow public vouchers if they are FREE (0 points). 
                # If they cost points, they MUST be redeemed first (ownership check).
                if voucher.is_public and voucher.point_cost == 0:
                    is_available = True
                elif ownership:
                    is_available = True
                else:
                    return Response({'error': 'You do not own this voucher. Please redeem it with points first.'}, status=400)

                if is_available:
                    # Validate min spend
                    if total_amount >= voucher.min_spend:
                        # Validate min level
                        current_level_id = wallet.get('current_level', {}).get('id') if wallet else None
                        if not voucher.min_points_level_id or (current_level_id and current_level_id >= voucher.min_points_level_id):
                            
                            # Note: We don't need to deduct points here anymore because 
                            # we enforced 'Redeem First' for any voucher that costs points.
                            # Points were already deducted during redemption.

                            if voucher.is_percentage:
                                voucher_discount = (total_amount * decimal.Decimal(str(voucher.discount_amount))) / 100
                            else:
                                voucher_discount = decimal.Decimal(str(voucher.discount_amount))
                            
                            # Mark as used if it was a CustomerVoucher
                            if ownership:
                                ownership.is_used = True
                                ownership.used_at = django.utils.timezone.now()
                            
                            print(f"[order-service] Voucher applied: {voucher.code} (-{voucher_discount})")
                        else:
                            return Response({'error': 'Voucher not available for your membership level'}, status=400)
                    else:
                        return Response({'error': f'Voucher requires minimum spend of {voucher.min_spend}'}, status=400)
            except Exception as e:
                print(f"[order-service] Voucher processing error: {e}")

        # Final amount after discount + shipping
        total_with_shipping = (total_amount - membership_discount - voucher_discount) + shipping_fee
        if total_with_shipping < 0:
            total_with_shipping = decimal.Decimal('0')
        total_with_shipping = total_with_shipping.quantize(decimal.Decimal('0.00'))

        # ── Step 3: Create Order in DB ────────────────────────
        initial_status = 'pending_confirmation' if payment_method == 'COD' else 'pending'
        print(f"[order-service] Step 3: Creating Order ({initial_status}) - total: {total_with_shipping}")
        order = Order.objects.create(
            customer_id=customer_id,
            status=initial_status,
            total_amount=total_with_shipping,
            membership_discount=membership_discount,
            voucher_discount=voucher_discount,
            voucher_code=voucher_code,
            points_generated=points_to_generate,
            shipping_address=shipping_address,
            shipping_fee=shipping_fee,
            shipping_method=shipping_method
        )
        _add_status_log(order, initial_status, "Order placed successfully.")
        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)

        # Update voucher usage if applicable
        if voucher_code and 'ownership' in locals() and ownership:
            ownership.is_used = True
            ownership.order_id = order.id
            ownership.used_at = django.utils.timezone.now()
            ownership.save()
            print(f"[order-service] CustomerVoucher {ownership.id} marked as used for Order {order.id}")

        # ── Step 4: Process Payment ───────────────────────────────────────────
        payment_data = {}
        if payment_method.upper() == 'COD':
            # For COD, bypass pay-service and set to pending_confirmation
            order.status = 'pending_confirmation'
            order.save()
            print(f"[order-service] Order {order.id} is COD -> pending_confirmation")
            payment_data = {'method': 'COD', 'status': 'pending'}
        else:
            # Online payment -> Call pay-service
            print(f"[order-service] Step 4: Calling pay-service for order {order.id}")
            try:
                pay_resp = requests.post(f"{PAY_SERVICE_URL}/payments/", json={
                    'order_id': order.id,
                    'customer_id': customer_id,
                    'amount': str(order.total_amount),
                    'method': payment_method,
                })
                _log("pay_service", pay_resp)
                payment_data = pay_resp.json()
            except Exception as e:
                order.status = 'failed'
                order.save()
                return Response({'error': f'pay-service unavailable: {e}'}, status=503)

            if payment_data.get('status') != 'success':
                order.status = 'failed'
                order.save()
                print(f"[order-service] Payment FAILED for order {order.id}")
                return Response({
                    'error': 'Payment failed',
                    'payment': payment_data,
                    'order_id': order.id
                }, status=402)

            # Payment succeeded -> update order status to processing
            order.status = 'processing'
            order.save()
            print(f"[order-service] Payment SUCCESS for order {order.id} - txn: {payment_data.get('transaction_id')}")

        # ── Step 4.5: Update Stock (Inventory) ───────────────────────────────
        print(f"[order-service] Step 4.5: Updating stock for order items...")
        for item_data in order_items_data:
            product_id = item_data['product_id']
            qty = item_data['quantity']
            try:
                inv_resp = requests.post(f"{PRODUCT_SERVICE_URL}/products/{product_id}/inventory/", json={
                    'change': -qty
                })
                print(f"[order-service] Stock updated for product {product_id}: -{qty} (Status: {inv_resp.status_code})")
            except Exception as e:
                print(f"[order-service] FAILED to update stock for product {product_id}: {e}")

        # ── Step 5: Defer Ship Service Call ────────────────────────────────────
        # Shipment creation is now deferred until Staff clicks "Mark Ready for Pickup" 
        # (Option B Flow).
        shipment_data = {'status': 'pending_dispatch'}
        print(f"[order-service] Order {order.id} Checkout Completed - Payment: {payment_data.get('status')} - Status: {order.status}")

        # Return full checkout summary
        return Response({
            'message': 'Order placed successfully!',
            'order': OrderSerializer(order).data,
            'payment': {
                'transaction_id': payment_data.get('transaction_id'),
                'method': payment_data.get('method'),
                'status': payment_data.get('status'),
            },
            'shipment': {
                'tracking_code': shipment_data.get('tracking_code'),
                'estimated_delivery': shipment_data.get('estimated_delivery'),
                'status': shipment_data.get('status'),
            }
        }, status=201)

    def get(self, request):
        status = request.query_params.get('status')
        days = request.query_params.get('days')
        customer_id = request.query_params.get('customer_id')

        queryset = Order.objects.all()

        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if status:
            queryset = queryset.filter(status=status)
        if days:
            from datetime import timedelta
            from django.utils import timezone
            cutoff = timezone.now() - timedelta(days=int(days))
            queryset = queryset.filter(created_at__gte=cutoff)

        orders = queryset.order_by('-created_at')
        # Pagination
        total_count = orders.count()
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_orders = orders[start:end]
        serializer = OrderSerializer(paginated_orders, many=True)
        
        return Response({
            'results': serializer.data,
            'total': total_count,
            'page': page,
            'page_size': page_size
        })


class OrderDetail(APIView):
    """
    GET   /orders/<id>/        → Order detail
    PATCH /orders/<id>/status/ → Update order status (internal)
    """
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            return Response(OrderSerializer(order).data)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)


class OrderStatusUpdate(APIView):
    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            new_status = request.data.get('status')
            valid = [s[0] for s in Order.STATUS_CHOICES]
            if new_status not in valid:
                return Response({'error': f'Invalid status. Must be one of: {valid}'}, status=400)
            order.status = new_status
            order.save()
            _add_status_log(order, new_status, "Manual status adjustment by Staff.")
            print(f"[order-service] Order {pk} status updated to: {new_status}")
            
            # If status becomes ready_for_pickup, dispatch to ship-service (Option B Flow)
            if new_status == 'ready_for_pickup':
                print(f"[order-service] Dispatching order {pk} to ship-service...")
                try:
                    ship_resp = requests.post(f"{SHIP_SERVICE_URL}/shipments/", json={
                        'order_id': order.id,
                        'customer_id': order.customer_id,
                        'address': order.shipping_address or 'Default Address',
                        'shipping_method': order.shipping_method,
                        'status': 'ready_for_pickup',
                    })
                    _log("ship_service_dispatch", ship_resp)
                except Exception as e:
                    print(f"[order-service] Failed to dispatch to ship-service: {e}")
            
            # Sync other non-ready_for_pickup updates if a shipment exists
            elif new_status in ['cancelled', 'completed', 'delivering']:
                try:
                    ship_resp = requests.patch(f"{SHIP_SERVICE_URL}/shipments/order/{order.id}/", json={'status': new_status})
                    print(f"[order-service] Synced status '{new_status}' to ship-service. Status Code: {ship_resp.status_code}")
                except Exception as e:
                    print(f"[order-service] Error syncing update to ship-service: {e}")
            
            # If completed -> Add points to customer
            if new_status == 'completed':
                try:
                    requests.post(f"{CUSTOMER_SERVICE_URL}/customers/{order.customer_id}/wallet/add-points/", json={
                        'amount': order.points_generated,
                        'description': f"Reward for order #{order.id}"
                    })
                    print(f"[order-service] Notified customer-service to award {order.points_generated} points.")
                except Exception as e:
                    print(f"[order-service] Error awarding points: {e}")

            return Response(OrderSerializer(order).data)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

class CheckPurchase(APIView):
    """
    GET /api/check-purchase/?customer_id={id}&product_id={id}
    Returns {"has_purchased": true/false}
    """
    def get(self, request):
        customer_id = request.query_params.get('customer_id')
        product_id = request.query_params.get('product_id') or request.query_params.get('book_id')  # backward compat
        
        if not customer_id or not product_id:
            return Response({'error': 'customer_id and product_id are required'}, status=400)
            
        has_purchased = OrderItem.objects.filter(
            order__customer_id=customer_id,
            product_id=product_id
        ).exists()
        
        return Response({'has_purchased': has_purchased})
class OrderCancelView(APIView):
    """
    POST /orders/<id>/cancel/ → Cancel an order if it's in pending or processing state.
    """
    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            if order.status not in ['pending', 'pending_confirmation', 'processing']:
                return Response({'error': f'Cannot cancel order in {order.status} state.'}, status=400)
            
            order.status = 'cancelled'
            order.save()
            _add_status_log(order, 'cancelled', "Order cancelled by user or system.")
            
            # Sync cancellation with ship-service
            try:
                requests.patch(f"{SHIP_SERVICE_URL}/shipments/order/{pk}/", json={'status': 'cancelled'})
            except: pass

            # Sync payment status with pay-service
            try:
                requests.patch(f"{PAY_SERVICE_URL}/payments/order/{pk}/", json={'status': 'cancelled'})
            except: pass

            print(f"[order-service] Order {pk} CANCELLED by user.")
            return Response(OrderSerializer(order).data)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

class OrderDeleteView(APIView):
    """
    DELETE /orders/<id>/delete/ → Delete an order if it's in cancelled state.
    """
    def delete(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            if order.status != 'cancelled':
                return Response({'error': 'Only cancelled orders can be deleted.'}, status=400)
            
            # Sync deletion with ship-service
            try:
                requests.delete(f"{SHIP_SERVICE_URL}/shipments/order/{pk}/")
            except: pass

            # Sync payment deletion with pay-service
            try:
                requests.delete(f"{PAY_SERVICE_URL}/payments/order/{pk}/")
            except: pass

            order.delete()
            print(f"[order-service] Order {pk} DELETED.")
            return Response({'message': 'Order deleted successfully.'}, status=200)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

class VoucherList(APIView):
    def get(self, request):
        vouchers = Voucher.objects.filter(is_active=True, is_public=True)
        return Response(VoucherSerializer(vouchers, many=True).data)

@method_decorator(csrf_exempt, name='dispatch')
class VoucherDetail(APIView):
    def get(self, request, code):
        try:
            voucher = Voucher.objects.get(code=code, is_active=True)
            return Response(VoucherSerializer(voucher).data)
        except Voucher.DoesNotExist:
            return Response({'error': 'Voucher not found'}, status=404)

class StaffVoucherListCreate(APIView):
    def get(self, request):
        vouchers = Voucher.objects.all().order_by('-created_at')
        return Response(VoucherSerializer(vouchers, many=True).data)
    
    def post(self, request):
        serializer = VoucherSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class StaffVoucherDetail(APIView):
    def get_object(self, pk):
        try: return Voucher.objects.get(pk=pk)
        except Voucher.DoesNotExist: return None

    def get(self, request, pk):
        v = self.get_object(pk)
        if not v: return Response({'error': 'Not found'}, status=404)
        return Response(VoucherSerializer(v).data)

    def put(self, request, pk):
        v = self.get_object(pk)
        if not v: return Response({'error': 'Not found'}, status=404)
        serializer = VoucherSerializer(v, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        v = self.get_object(pk)
        if not v: return Response({'error': 'Not found'}, status=404)
        v.delete()
        return Response(status=204)

class RedeemVoucher(APIView):
    def post(self, request):
        customer_id = request.data.get('customer_id')
        voucher_id = request.data.get('voucher_id')
        
        if not customer_id or not voucher_id:
            return Response({'error': 'customer_id and voucher_id are required'}, status=400)
            
        try:
            voucher = Voucher.objects.get(pk=voucher_id, is_active=True)
            
            # Check if customer already owns this voucher (avoid duplicates)
            existing = CustomerVoucher.objects.filter(customer_id=customer_id, voucher=voucher).exists()
            if existing:
                return Response({'error': 'You have already redeemed this voucher.'}, status=400)

            # Check Global limits
            if voucher.redeemed_quantity >= voucher.max_quantity:
                return Response({'error': 'This voucher has reached its redemption limit.'}, status=400)
            
            # Fetch customer wallet/level from customer-service
            try:
                cust_r = requests.get(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/")
                if cust_r.status_code != 200:
                    return Response({'error': 'Could not verify customer profile.'}, status=400)
                customer_data = cust_r.json()
                wallet = customer_data.get('wallet')
                current_level_id = wallet.get('current_level', {}).get('id') if wallet else None
            except Exception as e:
                return Response({'error': f'customer-service error: {e}'}, status=503)

            # Check Minimum Membership Level
            if voucher.min_points_level_id:
                if not current_level_id or current_level_id < voucher.min_points_level_id:
                    return Response({'error': 'Your membership level is not high enough to redeem this voucher.'}, status=400)

            # Check points (Call customer-service)
            if voucher.point_cost > 0:
                if not wallet or wallet.get('usable_points', 0) < voucher.point_cost:
                    return Response({'error': 'Insufficient points to redeem this voucher.'}, status=400)

                spend_payload = {
                    'amount': -voucher.point_cost,
                    'transaction_type': 'SPEND',
                    'description': f'Exchanged points for voucher {voucher.code}'
                }
                spend_r = requests.post(f"{CUSTOMER_SERVICE_URL}/customers/{customer_id}/wallet/add-points/", json=spend_payload)
                if spend_r.status_code != 200:
                    return Response({'error': 'Failed to deduct points.'}, status=400)
            
            # Create ownership
            CustomerVoucher.objects.create(
                customer_id=customer_id,
                voucher=voucher
            )
            
            # Update counter
            voucher.redeemed_quantity += 1
            voucher.save()
            
            return Response({'message': 'Voucher redeemed successfully!'}, status=201)
            
        except Voucher.DoesNotExist:
            return Response({'error': 'Voucher not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class CustomerVouchersView(APIView):
    def get(self, request, customer_id):
        vouchers = CustomerVoucher.objects.filter(customer_id=customer_id).order_by('-redeemed_at')
        return Response(CustomerVoucherSerializer(vouchers, many=True).data)
