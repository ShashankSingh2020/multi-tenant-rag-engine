from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import TimeStampedUUIDModel
from apps.organizations.models import Organization

User = get_user_model()


class AuditAction(models.TextChoices):
    USER_LOGIN = "USER_LOGIN", "User Login"
    MEMBER_INVITED = "MEMBER_INVITED", "Member Invited"
    MEMBER_REMOVED = "MEMBER_REMOVED", "Member Removed"
    PROJECT_CREATED = "PROJECT_CREATED", "Project Created"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "Document Uploaded"
    AI_QUERY_EXECUTED = "AI_QUERY_EXECUTED", "AI Query Executed"
    PLAN_UPGRADED = "PLAN_UPGRADED", "Plan Upgraded"


class AuditLog(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        db_index=True,
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        actor_email = self.actor.email if self.actor else "System"
        return f"[{self.created_at}] {self.organization.name} - {self.action} by {actor_email}"