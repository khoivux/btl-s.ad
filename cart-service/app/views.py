from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
import requests

PRODUCT_SERVICE_URL = "http://product-service:8000"


class CartCreate(APIView):
    def post(self, request):
        serializer = CartSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class CartItemView(APIView):
    def post(self, request):
        # Accept both product_id and book_id for backward compatibility
        product_id = request.data.get("product_id") or request.data.get("book_id")
        cart_id = request.data.get("cart")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response({"error": "product_id required"}, status=400)

        # Validate product exists in product-service
        try:
            r = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}/", timeout=5)
            if r.status_code != 200:
                return Response({"error": "Product not found"}, status=404)
        except Exception:
            return Response({"error": "Product service unavailable"}, status=503)

        try:
            cart, _ = Cart.objects.get_or_create(customer_id=cart_id)
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                product_id=product_id,
                defaults={'quantity': quantity}
            )
            if not created:
                item.quantity += quantity
                item.save()

            serializer = CartItemSerializer(item)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": "Failed to add to cart"}, status=500)

    def put(self, request, pk=None):
        if not pk:
            return Response({'error': 'Item ID required'}, status=400)
        try:
            item = CartItem.objects.get(pk=pk)
            new_quantity = request.data.get('quantity')
            if new_quantity is not None:
                item.quantity = int(new_quantity)
                item.save()
                return Response({'status': 'success', 'quantity': item.quantity})
            return Response({'error': 'No quantity provided'}, status=400)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=404)

    def delete(self, request, pk=None):
        if not pk:
            return Response({'error': 'Item ID required'}, status=400)
        try:
            item = CartItem.objects.get(pk=pk)
            item.delete()
            return Response({'status': 'deleted'})
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=404)


class ClearCart(APIView):
    def delete(self, request, customer_id):
        try:
            cart = Cart.objects.get(customer_id=customer_id)
            CartItem.objects.filter(cart=cart).delete()
            return Response({'status': 'cleared'})
        except Cart.DoesNotExist:
            return Response({'error': 'Cart not found'}, status=404)


class ViewCart(APIView):
    def get(self, request, customer_id):
        cart, _ = Cart.objects.get_or_create(customer_id=customer_id)
        items = CartItem.objects.filter(cart=cart)
        serializer = CartItemSerializer(items, many=True)
        return Response(serializer.data)