from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI Schema and Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Core Endpoints
    path("api/auth/", include("apps.accounts.urls")),
    path("api/organizations/", include("apps.organizations.urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    path("api/usage/", include("apps.usage.urls")),
    path("api/projects/", include("apps.projects.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/ai/", include("apps.ai.urls")),
    path("api/documents/", include("apps.documents.urls")),
]