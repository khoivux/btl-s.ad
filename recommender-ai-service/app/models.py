from django.db import models

class Review(models.Model):
    customer_id = models.IntegerField()
    book_id = models.IntegerField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, default='')
    customer_name = models.CharField(max_length=255, blank=True, default='User')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('customer_id', 'book_id')
        indexes = [
            models.Index(fields=['book_id']),
            models.Index(fields=['customer_id']),
        ]

    def __str__(self):
        return f"Review by {self.customer_id} for book {self.book_id} - Rating: {self.rating}"
