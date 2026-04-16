from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=255, default='123456')

    def __str__(self):
        return f"{self.name} ({self.email})"

class MembershipLevel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    min_points = models.IntegerField(default=0)
    discount_percentage = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class LoyaltyWallet(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wallet')
    usable_points = models.IntegerField(default=0)
    accumulated_points = models.IntegerField(default=0)
    current_level = models.ForeignKey(MembershipLevel, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Wallet for {self.customer.email} - {self.usable_points} pts"

class PointTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('EARN', 'Earned from purchase'),
        ('SPEND', 'Spent on voucher/reward'),
        ('EXPIRE', 'Expired')
    ]
    wallet = models.ForeignKey(LoyaltyWallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} {self.amount} - {self.wallet.customer.name}"

class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    name = models.CharField(max_length=100, help_text="Label e.g. 'Home', 'Office'")
    recipient_name = models.CharField(max_length=255, blank=True, null=True)
    recipient_phone = models.CharField(max_length=20, blank=True, null=True)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Vietnam')
    postal_code = models.CharField(max_length=20, blank=True, default='')
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', 'id']

    def save(self, *args, **kwargs):
        # Only one default address per customer
        if self.is_default:
            Address.objects.filter(
                customer=self.customer, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.name}] {self.street}, {self.city}"

class SearchHistory(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Search by {self.customer.name}: {self.query}"

class InteractionLog(models.Model):
    ACTION_TYPES = [
        ('VIEW_PRODUCT', 'Viewed Product'),
        ('ADD_TO_CART', 'Added to Cart'),
        ('REMOVE_FROM_CART', 'Removed from Cart')
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='interaction_logs')
    product_id = models.IntegerField()
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action_type} for Product {self.product_id} - {self.customer.name}"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant')
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='chat_messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role} to {self.customer.name} at {self.timestamp}"