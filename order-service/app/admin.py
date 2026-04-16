from django.contrib import admin
from .models import Order, OrderItem, Voucher, CustomerVoucher

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_id', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'customer_id')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product_id', 'product_name', 'quantity', 'unit_price')

@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_amount', 'is_percentage', 'min_spend', 'redeemed_quantity', 'max_quantity', 'is_active')
    list_filter = ('is_active', 'is_public')

@admin.register(CustomerVoucher)
class CustomerVoucherAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_id', 'voucher', 'is_used', 'redeemed_at', 'used_at')
