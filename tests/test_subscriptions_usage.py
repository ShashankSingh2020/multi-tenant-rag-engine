from django.test import TestCase
from apps.accounts.models import User
from apps.organizations.models import Organization, Membership, MembershipRole
from apps.subscriptions.models import Subscription, SubscriptionPlan, PlanTier
from apps.usage.services import record_ai_request_usage, record_document_upload_usage, get_active_usage_record


class TestSubscriptionsUsage(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="tenant@corp.com", password="Password123!")
        self.org = Organization.objects.create(name="Tenant Corp", slug="tenant-corp")
        Membership.objects.create(organization=self.org, user=self.user, role=MembershipRole.OWNER)

        self.plan = SubscriptionPlan.objects.create(
            name=PlanTier.FREE,
            max_ai_requests_per_month=10,
            max_documents=5,
            max_tokens_per_month=2000,
            price_cents=0,
        )
        self.sub = Subscription.objects.create(organization=self.org, plan=self.plan)

    def test_record_ai_request_increments_atomically(self):
        record_ai_request_usage(self.org.id, tokens_consumed=150)
        usage = get_active_usage_record(self.org.id)
        self.assertEqual(usage.ai_requests_count, 1)
        self.assertEqual(usage.total_tokens_used, 150)

    def test_record_document_upload_usage(self):
        record_document_upload_usage(self.org.id)
        usage = get_active_usage_record(self.org.id)
        self.assertEqual(usage.documents_uploaded_count, 1)
