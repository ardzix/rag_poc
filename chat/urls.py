"""
URLs untuk chat app
"""
from django.urls import path
from .views import ChatViewSet, ChatHistoryViewSet

urlpatterns = [
    path('', ChatViewSet.as_view({'post': 'create'}), name='chat'),
    path('history', ChatHistoryViewSet.as_view({'get': 'list'}), name='chat-history'),
]
