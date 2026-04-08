from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Address, MembershipLevel, LoyaltyWallet, PointTransaction, SearchHistory, InteractionLog, ChatMessage
from .serializers import CustomerSerializer, AddressSerializer, LoyaltyWalletSerializer, MembershipLevelSerializer, SearchHistorySerializer, InteractionLogSerializer, ChatMessageSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

import requests
CART_SERVICE_URL = "http://cart-service:8000"


@method_decorator(csrf_exempt, name='dispatch')
class CustomerListCreate(APIView):
    def get(self, request):
        customers = Customer.objects.all()
        return Response(CustomerSerializer(customers, many=True).data)

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if Customer.objects.filter(email=request.data.get('email')).exists():
            return Response({"error": "Email already exists"}, status=400)
        if serializer.is_valid():
            customer = Customer.objects.create(
                name=request.data['name'],
                email=request.data['email'],
                password=request.data.get('password', '123456'),
            )
            # Auto-create Loyalty Wallet
            bronze = MembershipLevel.objects.filter(name='Bronze').first()
            LoyaltyWallet.objects.create(customer=customer, current_level=bronze)
            
            try:
                requests.post(f"{CART_SERVICE_URL}/carts/", json={"customer_id": customer.id})
            except Exception:
                pass
            return Response(CustomerSerializer(customer).data, status=201)
        return Response(serializer.errors, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class CustomerDetail(APIView):
    def get(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            return Response(CustomerSerializer(customer).data)
        except Customer.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

    def put(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        
        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        try:
            customer = Customer.objects.get(email=email)
            if customer.password == password:
                return Response(CustomerSerializer(customer).data)
            return Response({"error": "Invalid password"}, status=401)
        except Customer.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class AddressListCreate(APIView):
    """GET/POST /customers/<customer_id>/addresses/"""
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=404)
        addresses = customer.addresses.all()
        return Response(AddressSerializer(addresses, many=True).data)

    def post(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=404)
        data = request.data.copy()
        data['customer'] = customer_id
        serializer = AddressSerializer(data=data)
        if serializer.is_valid():
            address = serializer.save()
            print(f"[customer-service] New address for customer {customer_id}: {address}")
            return Response(AddressSerializer(address).data, status=201)
        return Response(serializer.errors, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class AddressDetail(APIView):
    """PUT/DELETE /customers/<customer_id>/addresses/<pk>/"""
    def _get_address(self, customer_id, pk):
        try:
            return Address.objects.get(pk=pk, customer_id=customer_id)
        except Address.DoesNotExist:
            return None

    def put(self, request, customer_id, pk):
        address = self._get_address(customer_id, pk)
        if not address:
            return Response({'error': 'Not found'}, status=404)
        data = request.data.copy()
        data['customer'] = customer_id
        serializer = AddressSerializer(address, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, customer_id, pk):
        address = self._get_address(customer_id, pk)
        if not address:
            return Response({'error': 'Not found'}, status=404)
        address.delete()
        return Response(status=204)

    def patch(self, request, customer_id, pk):
        """Set this address as default."""
        address = self._get_address(customer_id, pk)
        if not address:
            return Response({'error': 'Not found'}, status=404)
        address.is_default = True
        address.save()
        return Response(AddressSerializer(address).data)


@method_decorator(csrf_exempt, name='dispatch')
class WalletDetail(APIView):
    def get(self, request, customer_id):
        try:
            wallet = LoyaltyWallet.objects.get(customer_id=customer_id)
            return Response(LoyaltyWalletSerializer(wallet).data)
        except LoyaltyWallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class AddPointsView(APIView):
    def post(self, request, customer_id):
        amount = int(request.data.get('amount') or 0)
        desc = request.data.get('description') or 'Purchase reward'
        txn_type = request.data.get('transaction_type') or ('EARN' if amount >= 0 else 'SPEND')
        
        try:
            wallet = LoyaltyWallet.objects.get(customer_id=customer_id)
            wallet.usable_points += amount
            
            # Only increase accumulated_points if earning
            if amount > 0:
                wallet.accumulated_points += amount
            
            # Re-evaluate Level (based on accumulated points)
            levels = MembershipLevel.objects.all().order_by('-min_points')
            for level in levels:
                if wallet.accumulated_points >= level.min_points:
                    wallet.current_level = level
                    break
            
            wallet.save()
            
            # Record Transaction
            PointTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=txn_type,
                description=desc
            )
            
            return Response(LoyaltyWalletSerializer(wallet).data)
        except LoyaltyWallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class PointTransactionListView(APIView):
    def get(self, request, customer_id):
        try:
            wallet = LoyaltyWallet.objects.get(customer_id=customer_id)
            transactions = wallet.transactions.all().order_by('-created_at')
            
            # Simple pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            start = (page - 1) * page_size
            end = start + page_size
            
            from .serializers import PointTransactionSerializer
            serializer = PointTransactionSerializer(transactions[start:end], many=True)
            
            return Response({
                'transactions': serializer.data,
                'has_more': transactions.count() > end,
                'total': transactions.count()
            })
        except LoyaltyWallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class MembershipLevelList(APIView):
    def get(self, request):
        levels = MembershipLevel.objects.all().order_by('id')
        return Response(MembershipLevelSerializer(levels, many=True).data)

# --- AI & Behavior Tracking Views ---

@method_decorator(csrf_exempt, name='dispatch')
class SearchHistoryView(APIView):
    def get(self, request, customer_id):
        history = SearchHistory.objects.filter(customer_id=customer_id).order_by('-created_at')[:50]
        return Response(SearchHistorySerializer(history, many=True).data)

    def post(self, request, customer_id):
        query = request.data.get('query')
        if not query:
            return Response({'error': 'Query is required'}, status=400)
        history = SearchHistory.objects.create(customer_id=customer_id, query=query)
        return Response(SearchHistorySerializer(history).data, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class InteractionLogView(APIView):
    def post(self, request, customer_id):
        book_id = request.data.get('book_id')
        action_type = request.data.get('action_type')
        if not book_id or not action_type:
            return Response({'error': 'book_id and action_type are required'}, status=400)
        log = InteractionLog.objects.create(customer_id=customer_id, book_id=book_id, action_type=action_type)
        return Response(InteractionLogSerializer(log).data, status=201)

@method_decorator(csrf_exempt, name='dispatch')
class ChatMessageListView(APIView):
    def get(self, request, customer_id):
        messages = ChatMessage.objects.filter(customer_id=customer_id).order_by('timestamp')
        return Response(ChatMessageSerializer(messages, many=True).data)

    def post(self, request, customer_id):
        role = request.data.get('role')
        content = request.data.get('content')
        if not role or not content:
            return Response({'error': 'role and content are required'}, status=400)
        msg = ChatMessage.objects.create(customer_id=customer_id, role=role, content=content)
        return Response(ChatMessageSerializer(msg).data, status=201)