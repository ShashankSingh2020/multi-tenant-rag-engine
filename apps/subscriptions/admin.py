from django.contrib import admin
from apps.subscriptions.models import SubscriptionPlan, Subscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "max_ai_requests_per_month", "max_documents")
    search_fields = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "is_active", "created_at")
    list_filter = ("is_active", "plan")
    search_fields = ("organization__name",)