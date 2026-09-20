from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, Membership, MembershipRole

User = get_user_model()


class OrganizationAndRBACTests(APITestCase):
    def setUp(self):
        # User 1 (Tenant A Owner)
        self.user_a = User.objects.create_user(
            email="tenant_a_owner@example.com",
            password="StrongPassword!2026",
            full_name="Tenant A Owner",
        )

        # User 2 (Tenant B Owner)
        self.user_b = User.objects.create_user(
            email="tenant_b_owner@example.com",
            password="StrongPassword!2026",
            full_name="Tenant B Owner",
        )

        # User 3 (Tenant A Normal Member)
        self.user_c = User.objects.create_user(
            email="tenant_a_member@example.com",
            password="StrongPassword!2026",
            full_name="Tenant A Member",
        )

        # Create Organization A
        self.client.force_authenticate(user=self.user_a)
        org_payload = {"name": "Acme Corporation"}
        res = self.client.post(reverse("organization-list-create"), org_payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.org_a_id = res.data["id"]
        self.org_a = Organization.objects.get(id=self.org_a_id)

    def test_organization_creator_becomes_owner(self):
        membership = Membership.objects.filter(
            user=self.user_a,
            organization=self.org_a,
        ).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, MembershipRole.OWNER)

    def test_tenant_isolation_user_b_cannot_view_org_a(self):
        # Authenticate as User B (Different Tenant)
        self.client.force_authenticate(user=self.user_b)

        # Listing orgs should return empty list for User B
        res_list = self.client.get(reverse("organization-list-create"))
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.data), 0)

        # Trying to access Org A directly by ID must fail (404 / 403)
        detail_url = reverse("organization-detail", kwargs={"id": self.org_a_id})
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_add_member(self):
        self.client.force_authenticate(user=self.user_a)
        members_url = reverse("organization-members", kwargs={"org_id": self.org_a_id})
        payload = {
            "user_email": self.user_c.email,
            "role": MembershipRole.MEMBER,
        }
        res = self.client.post(members_url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Membership.objects.filter(
                user=self.user_c,
                organization=self.org_a,
                role=MembershipRole.MEMBER,
            ).exists()
        )

    def test_regular_member_cannot_add_other_members(self):
        # First add user_c as MEMBER
        Membership.objects.create(
            user=self.user_c,
            organization=self.org_a,
            role=MembershipRole.MEMBER,
        )

        # Now authenticate as user_c and attempt to add another member
        self.client.force_authenticate(user=self.user_c)
        members_url = reverse("organization-members", kwargs={"org_id": self.org_a_id})
        payload = {
            "user_email": self.user_b.email,
            "role": MembershipRole.MEMBER,
        }
        res = self.client.post(members_url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)