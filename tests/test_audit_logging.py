from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, Membership, MembershipRole
from apps.audit.models import AuditLog, AuditAction
from apps.audit.services import AuditService

User = get_user_model()


class AuditLoggingTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@auditcompany.com",
            password="StrongPassword!2026",
            full_name="Company Owner",
        )
        self.member = User.objects.create_user(
            email="member@auditcompany.com",
            password="StrongPassword!2026",
            full_name="Regular Member",
        )
        self.outsider = User.objects.create_user(
            email="outsider@othercorp.com",
            password="StrongPassword!2026",
            full_name="Outside User",
        )

        self.org = Organization.objects.create(name="Audit Compliance Corp", slug="audit-corp")
        Membership.objects.create(user=self.owner, organization=self.org, role=MembershipRole.OWNER)
        Membership.objects.create(user=self.member, organization=self.org, role=MembershipRole.MEMBER)

        # Seed an audit log entry
        AuditService.log_event(
            organization=self.org,
            actor=self.owner,
            action=AuditAction.PROJECT_CREATED,
            details={"project_name": "Security Hardening"},
        )

        self.audit_url = reverse("audit-log-list")

    def test_owner_can_view_audit_logs(self):
        self.client.force_authenticate(user=self.owner)
        res = self.client.get(f"{self.audit_url}?org_id={self.org.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["action"], AuditAction.PROJECT_CREATED)
        self.assertEqual(res.data[0]["actor_email"], self.owner.email)

    def test_regular_member_forbidden_from_audit_logs(self):
        self.client.force_authenticate(user=self.member)
        res = self.client.get(f"{self.audit_url}?org_id={self.org.id}")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_outsider_forbidden_from_audit_logs(self):
        self.client.force_authenticate(user=self.outsider)
        res = self.client.get(f"{self.audit_url}?org_id={self.org.id}")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)