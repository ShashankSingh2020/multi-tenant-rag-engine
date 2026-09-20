from django.urls import path
from apps.usage.views import OrganizationUsageView

urlpatterns = [
    path("", OrganizationUsageView.as_view(), name="organization-usage"),
]