from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from apps.organizations.models import Organization
from apps.usage.models import UsageRecord
from apps.subscriptions.models import Subscription


class QuotaExceededException(Exception):
    pass


class UsageService:
    @staticmethod
    def get_or_create_monthly_record(organization: Organization) -> UsageRecord:
        now = timezone.now()
        record, _ = UsageRecord.objects.get_or_create(
            organization=organization,
            year=now.year,
            month=now.month,
        )
        return record

    @classmethod
    def get_organization_usage_summary(cls, organization: Organization) -> dict:
        now = timezone.now()
        record = cls.get_or_create_monthly_record(organization)
        subscription = getattr(organization, "subscription", None)

        if not subscription or not subscription.plan:
            max_ai = 0
            max_docs = 0
            max_tokens = 0
            plan_name = "NONE"
        else:
            plan = subscription.plan
            max_ai = plan.max_ai_requests_per_month
            max_docs = plan.max_documents
            max_tokens = plan.max_tokens_per_month
            plan_name = plan.name

        return {
            "plan": plan_name,
            "billing_period": f"{now.year}-{now.month:02d}",
            "ai_requests": record.ai_requests_count,
            "ai_request_limit": max_ai,
            "remaining_ai_requests": max(0, max_ai - record.ai_requests_count),
            "total_tokens_used": record.total_tokens_used,
            "token_limit": max_tokens,
            "remaining_tokens": max(0, max_tokens - record.total_tokens_used),
            "documents_uploaded": record.documents_uploaded_count,
            "document_limit": max_docs,
            "remaining_documents": max(0, max_docs - record.documents_uploaded_count),
        }

    @classmethod
    def verify_ai_quota(cls, organization: Organization) -> bool:
        summary = cls.get_organization_usage_summary(organization)
        if summary["remaining_ai_requests"] <= 0:
            raise QuotaExceededException("Monthly AI request quota exceeded for this organization.")
        return True

    @classmethod
    def record_ai_request_usage(cls, organization: Organization, tokens_used: int = 0):
        now = timezone.now()
        with transaction.atomic():
            record, _ = UsageRecord.objects.select_for_update().get_or_create(
                organization=organization,
                year=now.year,
                month=now.month,
            )
            record.ai_requests_count = F("ai_requests_count") + 1
            record.total_tokens_used = F("total_tokens_used") + tokens_used
            record.save(update_fields=["ai_requests_count", "total_tokens_used", "updated_at"])

    @classmethod
    def record_document_upload(cls, organization: Organization):
        now = timezone.now()
        with transaction.atomic():
            record, _ = UsageRecord.objects.select_for_update().get_or_create(
                organization=organization,
                year=now.year,
                month=now.month,
            )
            record.documents_uploaded_count = F("documents_uploaded_count") + 1
            record.save(update_fields=["documents_uploaded_count", "updated_at"])