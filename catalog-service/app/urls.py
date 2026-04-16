from django.urls import path
from .views import (
    ProductSyncView, ProductDeleteSyncView,
    CatalogSyncView, CatalogDeleteSyncView,
    CatalogListView, CatalogDetailView, CatalogCategorySyncView
)

urlpatterns = [
    # New product sync endpoints (used by product-service)
    path('sync/product/', ProductSyncView.as_view(), name='product-sync'),
    path('sync/product/<int:product_id>/', ProductDeleteSyncView.as_view(), name='product-delete-sync'),

    # Legacy book sync endpoints (backward compat)
    path('sync/book/', CatalogSyncView.as_view(), name='catalog-sync'),
    path('sync/book/<int:book_id>/', CatalogDeleteSyncView.as_view(), name='catalog-delete-sync'),

    # Category sync
    path('sync/category/<int:category_id>/', CatalogCategorySyncView.as_view(), name='catalog-category-sync'),

    # Product list / search / detail
    path('products/', CatalogListView.as_view(), name='catalog-products'),
    path('products/<int:book_id>/', CatalogDetailView.as_view(), name='catalog-product-detail'),
    path('search/', CatalogListView.as_view(), name='catalog-search'),

    # Legacy book aliases
    path('books/', CatalogListView.as_view(), name='catalog-books'),
    path('books/<int:book_id>/', CatalogDetailView.as_view(), name='catalog-detail'),
]
