from django.urls import path
from apps.projects.views import ProjectListCreateView, ProjectDetailView

urlpatterns = [
    path("", ProjectListCreateView.as_view(), name="project-list"),
    path("<uuid:pk>/", ProjectDetailView.as_view(), name="project-detail"),
]