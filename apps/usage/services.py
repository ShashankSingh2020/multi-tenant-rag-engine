from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import Throttled
from apps.subscriptions.models import Subscription
from apps.usage.models import UsageRecord


class UsageService:
    @staticmethod
    def get_or_create_usage_record(organization_id, for_update: bool = False):
        now = timezone.now()
        current_year = now.year
        current_month = now.month

        qs = UsageRecord.objects.all()
        if for_update:
            qs = qs.select_for_update()

        record = qs.filter(
            organization_id=organization_id,
            year=current_year,
            month=current_month,
        ).first()

        if not record:
            record, _ = UsageRecord.objects.get_or_create(
                organization_id=organization_id,
                year=current_year,
                month=current_month,
                defaults={
                    "total_tokens_used": 0,
                    "ai_requests_count": 0,
                    "documents_uploaded_count": 0,
                },
            )
        return record

    @classmethod
    def get_organization_usage_summary(cls, organization):
        org_id = organization.id if hasattr(organization, "id") else organization
        usage = cls.get_or_create_usage_record(org_id)
        sub = Subscription.objects.filter(organization_id=org_id).select_related("plan").first()
        plan = sub.plan if sub else None

        max_docs = plan.max_documents if plan else 10
        docs_used = usage.documents_uploaded_count
        remaining_docs = max(0, max_docs - docs_used)

        max_requests = plan.max_ai_requests_per_month if plan else 100
        requests_used = usage.ai_requests_count

        max_tokens = plan.max_tokens_per_month if plan else 50000
        tokens_used = usage.total_tokens_used

        return {
            "plan_name": plan.name if plan else "Free",
            "ai_requests_count": requests_used,
            "max_ai_requests": max_requests,
            "total_tokens_used": tokens_used,
            "max_tokens": max_tokens,
            "documents_uploaded_count": docs_used,
            "max_documents": max_docs,
            "remaining_documents": remaining_docs,
            "is_quota_exceeded": (
                (plan and docs_used >= max_docs)
                or (plan and requests_used >= max_requests)
                or (plan and tokens_used >= max_tokens)
            ),
        }

    @classmethod
    def check_quota(cls, organization_id, feature: str = "ai_requests", increment: int = 1):
        usage = cls.get_or_create_usage_record(organization_id)
        sub = Subscription.objects.filter(organization_id=organization_id).select_related("plan").first()
        if not sub or not sub.plan:
            return True

        if feature == "documents" and (usage.documents_uploaded_count + increment) > sub.plan.max_documents:
            raise Throttled(detail="Organization maximum document capacity reached.")
        elif feature == "ai_requests" and (usage.ai_requests_count + increment) > sub.plan.max_ai_requests_per_month:
            raise Throttled(detail="Organization monthly AI request limit reached.")
        elif feature == "tokens" and (usage.total_tokens_used + increment) > sub.plan.max_tokens_per_month:
            raise Throttled(detail="Organization monthly token limit reached.")
        return True

    @classmethod
    def record_document_upload(cls, organization_id):
        with transaction.atomic():
            usage = cls.get_or_create_usage_record(organization_id, for_update=True)
            sub = Subscription.objects.filter(organization_id=organization_id).select_related("plan").first()
            if sub and sub.plan and usage.documents_uploaded_count >= sub.plan.max_documents:
                raise Throttled(detail="Organization maximum document capacity reached.")
            UsageRecord.objects.filter(id=usage.id).update(
                documents_uploaded_count=F("documents_uploaded_count") + 1
            )

    @classmethod
    def record_ai_query(cls, organization_id, tokens_consumed: int = 0):
        with transaction.atomic():
            usage = cls.get_or_create_usage_record(organization_id, for_update=True)
            sub = Subscription.objects.filter(organization_id=organization_id).select_related("plan").first()
            if sub and sub.plan:
                if usage.ai_requests_count >= sub.plan.max_ai_requests_per_month:
                    raise Throttled(detail="Organization monthly AI request limit reached.")
                if (usage.total_tokens_used + tokens_consumed) > sub.plan.max_tokens_per_month:
                    raise Throttled(detail="Organization monthly token limit reached.")

            UsageRecord.objects.filter(id=usage.id).update(
                ai_requests_count=F("ai_requests_count") + 1,
                total_tokens_used=F("total_tokens_used") + tokens_consumed,
            )


# Backward-compatible function bindings
get_active_usage_record = UsageService.get_or_create_usage_record
record_ai_request_usage = UsageService.record_ai_query
record_document_upload_usage = UsageService.record_document_upload
