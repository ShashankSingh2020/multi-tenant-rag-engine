from django.urls import path
from apps.subscriptions.views import (
    SubscriptionPlanListView,
    CurrentSubscriptionView,
    ChangeSubscriptionPlanView,
)

urlpatterns = [
    path("plans/", SubscriptionPlanListView.as_view(), name="subscription-plans"),
    path("current/", CurrentSubscriptionView.as_view(), name="subscription-current"),
    path("change/", ChangeSubscriptionPlanView.as_view(), name="subscription-change"),
]