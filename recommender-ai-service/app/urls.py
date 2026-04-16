from django.urls import path
from .views import RecommendationApiView, ConsultantChatView, VectorIndexProductsView

urlpatterns = [
    path('recommendations/', RecommendationApiView.as_view(), name='recommendation_list'),
    path('recommendations/<int:customer_id>/', RecommendationApiView.as_view(), name='recommendation_detail'),
    path('chat/consultant/<int:customer_id>/', ConsultantChatView.as_view(), name='consultant_chat'),
    path('index-kb/', VectorIndexProductsView.as_view(), name='index_kb'),
]
