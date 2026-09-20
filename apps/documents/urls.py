from django.urls import path
from apps.documents.views import DocumentListCreateView, DocumentDetailView

urlpatterns = [
    path("project/<uuid:project_id>/", DocumentListCreateView.as_view(), name="document-list-create"),
    path("<uuid:id>/", DocumentDetailView.as_view(), name="document-detail"),
]