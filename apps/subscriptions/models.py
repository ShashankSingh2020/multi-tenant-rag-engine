from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel
from apps.organizations.models import Organization


class PlanTier(models.TextChoices):
    FREE = "FREE", "Free"
    PRO = "PRO", "Pro"
    BUSINESS = "BUSINESS", "Business"


class SubscriptionPlan(TimeStampedUUIDModel):
    name = models.CharField(max_length=50, choices=PlanTier.choices, unique=True)
    max_ai_requests_per_month = models.PositiveIntegerField(default=100)
    max_documents = models.PositiveIntegerField(default=10)
    max_tokens_per_month = models.PositiveIntegerField(default=50000)
    price_cents = models.PositiveIntegerField(default=0)  # Ready for Stripe integration

    class Meta:
        db_table = "subscription_plans"
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"

    def __str__(self):
        return f"{self.name} Plan"


class Subscription(TimeStampedUUIDModel):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
        db_index=True,
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    is_active = models.BooleanField(default=True)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subscriptions"
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.organization.name} -> {self.plan.name}"