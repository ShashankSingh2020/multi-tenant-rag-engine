from rest_framework import generics, status, permissions, views
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.organizations.models import (
    Organization,
    Membership,
    MembershipRole,
    Invitation,
    InvitationStatus,
)
from apps.organizations.serializers import (
    OrganizationSerializer,
    MembershipSerializer,
    InvitationCreateSerializer,
    InvitationAcceptSerializer,
)

User = get_user_model()


class OrganizationListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
            is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        serializer.save()


class OrganizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        membership = Membership.objects.filter(user=request.user, organization=obj).first()
        if not membership:
            raise PermissionDenied("You are not a member of this organization.")
        if request.method in ["PUT", "PATCH"] and membership.role not in [MembershipRole.ADMIN, MembershipRole.OWNER]:
            raise PermissionDenied("Only Admins or Owners can update organization details.")
        if request.method == "DELETE" and membership.role != MembershipRole.OWNER:
            raise PermissionDenied("Only the Owner can delete the organization.")


class OrganizationMemberListCreateView(generics.ListCreateAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_org_and_caller(self):
        org = get_object_or_404(Organization, id=self.kwargs["org_id"])
        caller = Membership.objects.filter(user=self.request.user, organization=org).first()
        if not caller:
            raise PermissionDenied("You are not a member of this organization.")
        return org, caller

    def get_queryset(self):
        org, _ = self.get_org_and_caller()
        return Membership.objects.filter(organization=org).select_related("user")

    def create(self, request, *args, **kwargs):
        org, caller = self.get_org_and_caller()
        if caller.role not in [MembershipRole.ADMIN, MembershipRole.OWNER]:
            raise PermissionDenied("Insufficient permissions to add members.")

        target_role = request.data.get("role", MembershipRole.MEMBER)
        if target_role == MembershipRole.OWNER and caller.role != MembershipRole.OWNER:
            raise PermissionDenied("Only an existing OWNER can transfer or create OWNER roles.")

        user_email = request.data.get("user_email")
        if not user_email:
            raise ValidationError({"user_email": "This field is required."})

        target_user = get_object_or_404(User, email=user_email)
        if Membership.objects.filter(user=target_user, organization=org).exists():
            raise ValidationError({"user_email": "User is already an active member."})

        membership = Membership.objects.create(user=target_user, organization=org, role=target_role)
        return Response(self.get_serializer(membership).data, status=status.HTTP_201_CREATED)


class OrganizationMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        org = get_object_or_404(Organization, id=self.kwargs["org_id"])
        if not Membership.objects.filter(user=self.request.user, organization=org).exists():
            raise PermissionDenied("Access denied to organization members.")
        return Membership.objects.filter(organization=org)

    def perform_update(self, serializer):
        org = get_object_or_404(Organization, id=self.kwargs["org_id"])
        caller = get_object_or_404(Membership, user=self.request.user, organization=org)
        target = self.get_object()

        if caller.role not in [MembershipRole.ADMIN, MembershipRole.OWNER]:
            raise PermissionDenied("Only Admins or Owners can modify roles.")

        new_role = serializer.validated_data.get("role")
        if new_role == MembershipRole.OWNER and caller.role != MembershipRole.OWNER:
            raise PermissionDenied("Only an OWNER can promote another user to OWNER.")
        if target.role == MembershipRole.OWNER and caller.user != target.user:
            raise PermissionDenied("Cannot modify the role of an Organization OWNER.")

        serializer.save()

    def perform_destroy(self, instance):
        org = instance.organization
        caller = get_object_or_404(Membership, user=self.request.user, organization=org)
        if caller.role not in [MembershipRole.ADMIN, MembershipRole.OWNER]:
            raise PermissionDenied("Insufficient permissions to remove members.")
        if instance.role == MembershipRole.OWNER:
            raise ValidationError("Organization Owner cannot be removed.")
        instance.delete()


class OrganizationInviteCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, org_id):
        membership = get_object_or_404(
            Membership,
            organization_id=org_id,
            user=request.user,
            role__in=[MembershipRole.OWNER, MembershipRole.ADMIN],
        )

        desired_role = request.data.get("role", MembershipRole.MEMBER)
        if desired_role == MembershipRole.OWNER:
            raise PermissionDenied("Cannot invite users directly as OWNER.")

        serializer = InvitationCreateSerializer(
            data=request.data,
            context={"organization": membership.organization},
        )
        serializer.is_valid(raise_exception=True)
        invite = serializer.save(organization=membership.organization, invited_by=request.user)

        return Response(
            {
                "message": "Invitation created successfully.",
                "id": str(invite.id),
                "email": invite.email,
                "role": invite.role,
                "token": invite.token,
                "expires_at": invite.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class OrganizationInviteAcceptView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        invite = get_object_or_404(Invitation, token=token, status=InvitationStatus.PENDING)
        if invite.is_expired:
            invite.status = InvitationStatus.REVOKED
            invite.save(update_fields=["status"])
            return Response({"detail": "This invitation has expired."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            membership, _ = Membership.objects.get_or_create(
                organization=invite.organization,
                user=request.user,
                defaults={"role": invite.role},
            )
            invite.status = InvitationStatus.ACCEPTED
            invite.save(update_fields=["status"])

        return Response(
            {
                "message": f"Successfully joined {invite.organization.name}.",
                "organization_id": str(invite.organization.id),
                "role": invite.role,
            },
            status=status.HTTP_200_OK,
        )
