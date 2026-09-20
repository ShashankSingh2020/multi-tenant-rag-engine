from django.contrib import admin
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "organization", "actor", "created_at")
    list_filter = ("action", "organization")
    search_fields = ("action", "organization__name", "actor__email")
    readonly_fields = ("created_at",)