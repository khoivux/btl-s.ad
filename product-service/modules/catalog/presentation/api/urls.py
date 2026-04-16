from django.urls import path
from .views.product_view import ProductListCreateAPI, ProductDetailAPI, ProductInventoryAPI
from .views.category_view import CategoryListCreateAPI, CategoryDetailAPI

urlpatterns = [
    # Products
    path('', ProductListCreateAPI.as_view()),
    path('<int:pk>/', ProductDetailAPI.as_view()),
    path('<int:pk>/inventory/', ProductInventoryAPI.as_view()),

    # Categories
    path('categories/', CategoryListCreateAPI.as_view()),
    path('categories/<int:pk>/', CategoryDetailAPI.as_view()),
]
