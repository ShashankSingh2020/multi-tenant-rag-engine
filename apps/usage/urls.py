from django.urls import path
from apps.usage.views import UsageSummaryView

urlpatterns = [
    path("summary/", UsageSummaryView.as_view(), name="usage-summary"),
]
