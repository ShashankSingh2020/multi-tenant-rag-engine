from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.organizations.models import (
    Organization,
    Membership,
    MembershipRole,
    Invitation,
    InvitationStatus,
)


class TeamInvitationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name="Team Alpha", slug="team-alpha")
        self.owner = User.objects.create_user(email="owner@alpha.com", password="Password123!")
        self.member = User.objects.create_user(email="regular@alpha.com", password="Password123!")
        self.invitee = User.objects.create_user(email="newjoiner@alpha.com", password="Password123!")

        Membership.objects.create(organization=self.org, user=self.owner, role=MembershipRole.OWNER)
        Membership.objects.create(organization=self.org, user=self.member, role=MembershipRole.MEMBER)

    def test_owner_can_generate_invitation(self):
        self.client.force_authenticate(user=self.owner)
        res = self.client.post(
            f"/api/organizations/{self.org.id}/invites/",
            {"email": "newjoiner@alpha.com", "role": MembershipRole.ADMIN},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Invitation.objects.filter(email="newjoiner@alpha.com").exists())

    def test_regular_member_forbidden_from_inviting(self):
        self.client.force_authenticate(user=self.member)
        res = self.client.post(
            f"/api/organizations/{self.org.id}/invites/",
            {"email": "stranger@alpha.com", "role": MembershipRole.MEMBER},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_accept_invitation_and_join_org(self):
        invite = Invitation.objects.create(
            organization=self.org,
            email="newjoiner@alpha.com",
            role=MembershipRole.MEMBER,
            invited_by=self.owner,
        )
        self.client.force_authenticate(user=self.invitee)
        res = self.client.post(
            "/api/organizations/invites/accept/",
            {"token": invite.token},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(Membership.objects.filter(organization=self.org, user=self.invitee).exists())
        invite.refresh_from_db()
        self.assertEqual(invite.status, InvitationStatus.ACCEPTED)
