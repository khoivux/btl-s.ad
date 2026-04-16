from django.urls import path
from .views import ReviewListCreate, ReviewReadAll

urlpatterns = [
    path('reviews/all/', ReviewReadAll.as_view(), name='reviews-all'),
    path('reviews/<int:product_id>/', ReviewListCreate.as_view(), name='product-reviews'),
    path('reviews/', ReviewListCreate.as_view(), name='upsert-review'),
]
