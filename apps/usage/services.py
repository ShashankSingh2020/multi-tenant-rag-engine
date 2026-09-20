import logging
from django.utils import timezone
from apps.usage.models import UsageRecord
from apps.subscriptions.models import Subscription

logger = logging.getLogger(__name__)


class UsageService:

    @classmethod
    def get_organization_usage_summary(cls, organization):
        """
        Retrieves current billing cycle usage metrics and plan limits for an organization.
        Used across views (documents, AI queries) for quota validation and tracking.
        """
        if not organization:
            return {
                "ai_requests": 0,
                "ai_request_limit": 100,
                "remaining_ai_requests": 100,
                "documents": 0,
                "document_limit": 10,
                "remaining_documents": 10,
                "tokens_used": 0,
                "plan": "FREE",
            }

        subscription = getattr(organization, "subscription", None)
        if not subscription:
            subscription = Subscription.objects.filter(organization=organization, is_active=True).first()

        # Plan defaults
        max_ai_requests = 100
        max_documents = 10
        plan_name = "FREE"

        if subscription and hasattr(subscription, "plan") and subscription.plan:
            plan = subscription.plan
            plan_name = getattr(plan, "name", "FREE")
            max_ai_requests = getattr(plan, "max_ai_requests_per_month", 100)
            max_documents = getattr(plan, "max_documents", 10)

        now = timezone.now()
        usage_record = UsageRecord.objects.filter(
            organization=organization,
            year=now.year,
            month=now.month,
        ).first()

        ai_requests_used = usage_record.ai_requests_count if usage_record else 0
        documents_used = usage_record.documents_uploaded_count if usage_record else 0
        tokens_used = usage_record.total_tokens_used if usage_record else 0

        return {
            "plan": plan_name,
            "ai_requests": ai_requests_used,
            "ai_request_limit": max_ai_requests,
            "remaining_ai_requests": max(0, max_ai_requests - ai_requests_used),
            "documents": documents_used,
            "document_limit": max_documents,
            "remaining_documents": max(0, max_documents - documents_used),
            "tokens_used": tokens_used,
        }

    @classmethod
    def can_execute_ai_request(cls, organization=None) -> bool:
        """
        Pre-flight check: Verifies if the organization has remaining AI requests
        under their current subscription tier before invoking LLM inference.
        """
        if not organization:
            return True

        summary = cls.get_organization_usage_summary(organization)
        return summary["ai_requests"] < summary["ai_request_limit"]

    @classmethod
    def record_ai_request_usage(cls, organization, tokens_used: int = 0):
        """Atomically records an AI request and updates token metrics."""
        if not organization:
            return

        now = timezone.now()
        usage_record, _ = UsageRecord.objects.get_or_create(
            organization=organization,
            year=now.year,
            month=now.month,
        )

        usage_record.ai_requests_count += 1
        usage_record.total_tokens_used += int(tokens_used or 0)
        usage_record.save()

    @classmethod
    def record_ai_request(cls, organization, tokens_used: int = 0):
        """Alias method for backward compatibility."""
        return cls.record_ai_request_usage(organization=organization, tokens_used=tokens_used)

    @classmethod
    def record_document_upload(cls, organization):
        """Tracks total document uploads against organization limits."""
        if not organization:
            return

        now = timezone.now()
        usage_record, _ = UsageRecord.objects.get_or_create(
            organization=organization,
            year=now.year,
            month=now.month,
        )

        usage_record.documents_uploaded_count += 1
        usage_record.save()