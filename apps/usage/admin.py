from django.contrib import admin
from apps.usage.models import UsageRecord


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ("organization", "year", "month", "ai_requests_count", "documents_uploaded_count", "total_tokens_used")
    list_filter = ("year", "month", "organization")
    search_fields = ("organization__name",)