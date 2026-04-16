from django.db import models

class Review(models.Model):
    customer_id = models.IntegerField()
    product_id = models.IntegerField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, default='')
    customer_name = models.CharField(max_length=255, blank=True, default='User')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer_id', 'product_id')
        indexes = [
            models.Index(fields=['product_id']),
            models.Index(fields=['customer_id']),
        ]

    def __str__(self):
        return f"Review by {self.customer_id} for product {self.product_id} - Rating: {self.rating}"
