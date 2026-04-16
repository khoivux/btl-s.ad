from django.db import models

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('pending_confirmation', 'Pending Confirmation'),
        ('processing', 'Processing'),
        ('ready_for_pickup', 'Ready for Pickup'),
        ('delivering', 'Delivering'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    customer_id = models.IntegerField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Loyalty & Discounts
    membership_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    voucher_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    voucher_code = models.CharField(max_length=100, blank=True, default='')
    points_generated = models.IntegerField(default=0)
    
    shipping_address = models.TextField(blank=True, default='')
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_method = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_id} - {self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()
    product_name = models.CharField(max_length=255, default='')  # Snapshot
    item_image_url = models.TextField(blank=True, default='')   # Snapshot
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Snapshot price

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"OrderItem #{self.id} - Product {self.product_id} x{self.quantity}"

class Voucher(models.Model):
    code = models.CharField(max_length=100, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=False)
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_points_level_id = models.IntegerField(null=True, blank=True, help_text="MembershipLevel ID from customer-service")
    point_cost = models.IntegerField(default=0)
    max_quantity = models.IntegerField(default=100)
    redeemed_quantity = models.IntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.redeemed_quantity}/{self.max_quantity})"

class CustomerVoucher(models.Model):
    customer_id = models.IntegerField()
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='customer_vouchers')
    is_used = models.BooleanField(default=False)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    order_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Customer {self.customer_id} - {self.voucher.code} (Used: {self.is_used})"

class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=50)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.order.id} -> {self.status} at {self.created_at}"
