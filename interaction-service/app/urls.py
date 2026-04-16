from django.urls import path
from .views import LogInteraction, GetUserLogs

urlpatterns = [
    path('logs/', LogInteraction.as_view(), name='log_interaction'),
    path('logs/user/<int:user_id>/', GetUserLogs.as_view(), name='get_user_logs'),
]
