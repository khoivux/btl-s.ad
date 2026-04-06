from django.urls import path
from .views import RecommendationApiView, ConsultantChatView, VectorIndexBooksView

urlpatterns = [
    path('recommendations/', RecommendationApiView.as_view(), name='recommendation_list'),
    path('recommendations/<int:customer_id>/', RecommendationApiView.as_view(), name='recommendation_personalized'),
    
    # AI consultant chat
    path('chat/consultant/<int:customer_id>/', ConsultantChatView.as_view(), name='consultant_chat'),
    
    # AI maintenance
    path('index-kb/', VectorIndexBooksView.as_view(), name='index_kb'),
]
