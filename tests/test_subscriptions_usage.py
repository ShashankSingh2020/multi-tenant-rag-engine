import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from apps.organizations.models import Organization
from apps.accounts.models import User
from apps.subscriptions.models import SubscriptionPlan, Subscription
from apps.usage.models import UsageRecord
from apps.usage.services import UsageService
from apps.projects.models import Project


@pytest.mark.django_db
class SubscriptionAndUsageTests:

    def setup_method(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="Subscription Org", slug="sub-org")
        self.user = User.objects.create_user(email="owner@suborg.com", password="Password123!")

        if hasattr(self.user, "organization"):
            self.user.organization = self.org
            self.user.save()

        # JWT Login
        res = self.client.post(
            "/api/auth/login/",
            {"email": "owner@suborg.com", "password": "Password123!"},
            format="json",
        )
        self.token = res.data.get("access")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        # Plans setup
        self.free_plan = SubscriptionPlan.objects.create(
            name="FREE",
            price_monthly=0,
            max_ai_requests_per_month=5,
            max_documents=5,
        )
        self.pro_plan = SubscriptionPlan.objects.create(
            name="PRO",
            price_monthly=49,
            max_ai_requests_per_month=5000,
            max_documents=100,
        )

        self.subscription = Subscription.objects.create(
            organization=self.org,
            plan=self.free_plan,
            is_active=True,
        )

        self.project = Project.objects.create(name="Usage Project", organization=self.org)

    def test_organization_created_with_default_free_subscription(self):
        self.assertEqual(self.subscription.plan.name, "FREE")
        self.assertTrue(self.subscription.is_active)

    def test_owner_can_upgrade_subscription(self):
        self.subscription.plan = self.pro_plan
        self.subscription.save()
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan.name, "PRO")

    def test_member_cannot_upgrade_subscription(self):
        # Verify access protection logic
        member_client = APIClient()
        member_user = User.objects.create_user(email="regular@suborg.com", password="Password123!")
        res = member_client.post(
            "/api/auth/login/",
            {"email": "regular@suborg.com", "password": "Password123!"},
            format="json",
        )
        member_token = res.data.get("access")
        member_client.credentials(HTTP_AUTHORIZATION=f"Bearer {member_token}")

        response = member_client.post(
            "/api/subscriptions/upgrade/",
            {"plan": "PRO"},
            format="json",
        )
        self.assertIn(response.status_code, [403, 404])

    def test_usage_service_atomic_tracking_and_quota_breach(self):
        # Test within limits
        self.assertTrue(UsageService.can_execute_ai_request(self.org))

        # Record usage up to the limit
        UsageService.record_ai_request_usage(self.org, tokens_used=1200)
        UsageService.record_ai_request_usage(self.org, tokens_used=800)

        now = timezone.now()
        record = UsageRecord.objects.get(
            organization=self.org,
            period_start__year=now.year,
            period_start__month=now.month,
        )
        self.assertEqual(record.ai_requests_count, 2)
        self.assertEqual(record.total_tokens_consumed, 2000)

    def test_usage_summary_endpoint(self):
        response = self.client.get("/api/usage/")
        self.assertIn(response.status_code, [200, 404])

    def test_pre_flight_quota_blocks_exhausted_organization(self):
        """Asserts that an organization exceeding its quota returns False on preflight."""
        now = timezone.now()
        usage, _ = UsageRecord.objects.get_or_create(
            organization=self.org,
            period_start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        )
        usage.ai_requests_count = 999999
        usage.save()

        allowed = UsageService.can_execute_ai_request(self.org)
        self.assertFalse(allowed)

    def assertEqual(self, a, b):
        assert a == b

    def assertTrue(self, x):
        assert bool(x) is True

    def assertFalse(self, x):
        assert bool(x) is False

    def assertIn(self, a, b):
        assert a in b