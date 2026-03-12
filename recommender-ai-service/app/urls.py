from django.urls import path
from .views import ReviewListCreate

urlpatterns = [
    path('reviews/<int:book_id>/', ReviewListCreate.as_view(), name='book-reviews'),
    path('reviews/', ReviewListCreate.as_view(), name='upsert-review'),
]
