from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, Membership, MembershipRole
from apps.subscriptions.models import SubscriptionPlan, Subscription, PlanTier
from apps.usage.services import UsageService, QuotaExceededException

User = get_user_model()


class SubscriptionAndUsageTests(APITestCase):
    def setUp(self):
        # Create standard plans in test database
        self.free_plan = SubscriptionPlan.objects.create(
            name=PlanTier.FREE,
            max_ai_requests_per_month=2,
            max_documents=5,
            max_tokens_per_month=1000,
            price_cents=0,
        )
        self.pro_plan = SubscriptionPlan.objects.create(
            name=PlanTier.PRO,
            max_ai_requests_per_month=2000,
            max_documents=100,
            max_tokens_per_month=1000000,
            price_cents=2900,
        )

        # Users
        self.owner = User.objects.create_user(
            email="owner@tenant.com",
            password="StrongPassword!2026",
            full_name="Tenant Owner",
        )
        self.member = User.objects.create_user(
            email="member@tenant.com",
            password="StrongPassword!2026",
            full_name="Tenant Member",
        )

        # Authenticate as owner and create organization (auto-attaches FREE plan)
        self.client.force_authenticate(user=self.owner)
        res = self.client.post(reverse("organization-list-create"), {"name": "AI Corp"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.org_id = res.data["id"]
        self.org = Organization.objects.get(id=self.org_id)

        # Attach member to organization
        Membership.objects.create(
            user=self.member,
            organization=self.org,
            role=MembershipRole.MEMBER,
        )

    def test_organization_created_with_default_free_subscription(self):
        subscription = Subscription.objects.filter(organization=self.org).first()
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.plan.name, PlanTier.FREE)

    def test_owner_can_upgrade_subscription(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("subscription-change")
        payload = {
            "organization_id": str(self.org.id),
            "plan_name": PlanTier.PRO,
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.org.subscription.refresh_from_db()
        self.assertEqual(self.org.subscription.plan.name, PlanTier.PRO)

    def test_member_cannot_upgrade_subscription(self):
        self.client.force_authenticate(user=self.member)
        url = reverse("subscription-change")
        payload = {
            "organization_id": str(self.org.id),
            "plan_name": PlanTier.PRO,
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_usage_summary_endpoint(self):
        self.client.force_authenticate(user=self.member)
        url = f"{reverse('organization-usage')}?org_id={self.org.id}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["plan"], PlanTier.FREE)
        self.assertEqual(res.data["ai_requests"], 0)
        self.assertEqual(res.data["ai_request_limit"], 2)

    def test_usage_service_atomic_tracking_and_quota_breach(self):
        # First check passes
        self.assertTrue(UsageService.verify_ai_quota(self.org))

        # Record 1st AI request
        UsageService.record_ai_request_usage(self.org, tokens_used=150)
        summary = UsageService.get_organization_usage_summary(self.org)
        self.assertEqual(summary["ai_requests"], 1)
        self.assertEqual(summary["total_tokens_used"], 150)
        self.assertEqual(summary["remaining_ai_requests"], 1)

        # Record 2nd AI request (hits limit of 2)
        UsageService.record_ai_request_usage(self.org, tokens_used=200)
        summary = UsageService.get_organization_usage_summary(self.org)
        self.assertEqual(summary["ai_requests"], 2)
        self.assertEqual(summary["remaining_ai_requests"], 0)

        # 3rd request should raise QuotaExceededException
        with self.assertRaises(QuotaExceededException):
            UsageService.verify_ai_quota(self.org)