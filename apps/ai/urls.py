from django.urls import path
from apps.ai.views import RAGQueryView

urlpatterns = [
    path("query/", RAGQueryView.as_view(), name="ai-rag-query"),
]