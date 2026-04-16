from django.urls import path
from .views import StaffProductManager, StaffProductDetailManager, StaffLogin

urlpatterns = [
    path('staff/login/', StaffLogin.as_view(), name='staff-login'),
    path('staff/products/', StaffProductManager.as_view(), name='staff-products'),
    path('staff/products/<int:pk>/', StaffProductDetailManager.as_view(), name='staff-products-detail'),
]
