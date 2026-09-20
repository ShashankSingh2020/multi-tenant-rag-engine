from django.db import models
from apps.common.models import TimeStampedUUIDModel
from apps.organizations.models import Organization


class UsageRecord(TimeStampedUUIDModel):
    """
    Aggregated usage per organization for a specific billing month (year and month).
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="usage_records",
        db_index=True,
    )
    year = models.PositiveIntegerField(db_index=True)
    month = models.PositiveSmallIntegerField(db_index=True)

    ai_requests_count = models.PositiveIntegerField(default=0)
    total_tokens_used = models.PositiveIntegerField(default=0)
    documents_uploaded_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "usage_records"
        verbose_name = "Usage Record"
        verbose_name_plural = "Usage Records"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "year", "month"],
                name="unique_org_monthly_usage",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "year", "month"]),
        ]

    def __str__(self):
        return f"{self.organization.name} Usage ({self.month}/{self.year})"