from rest_framework import serializers
from .models import Order, OrderItem, Voucher, CustomerVoucher, OrderStatusLog

class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product_id', 'product_name', 'item_image_url', 'quantity', 'unit_price', 'subtotal']

class OrderStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusLog
        fields = ['status', 'notes', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusLogSerializer(source='status_logs', many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_id', 'total_amount', 'status', 
            'membership_discount', 'voucher_discount', 'voucher_code', 'points_generated',
            'shipping_address', 'shipping_fee', 'shipping_method', 
            'created_at', 'updated_at', 'items', 'status_history'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = [
            'id', 'code', 'discount_amount', 'is_percentage', 
            'min_spend', 'min_points_level_id', 'point_cost', 
            'max_quantity', 'redeemed_quantity', 'is_public',
            'is_active', 'expiry_date', 'created_at'
        ]
        read_only_fields = ['id', 'redeemed_quantity', 'created_at']

class CustomerVoucherSerializer(serializers.ModelSerializer):
    voucher_details = VoucherSerializer(source='voucher', read_only=True)
    
    class Meta:
        model = CustomerVoucher
        fields = [
            'id', 'customer_id', 'voucher', 'voucher_details', 
            'is_used', 'redeemed_at', 'used_at', 'order_id'
        ]
        read_only_fields = ['id', 'redeemed_at', 'used_at', 'order_id']
