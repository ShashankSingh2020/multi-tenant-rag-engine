from rest_framework import generics, status, permissions, views
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse

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
from apps.organizations.permissions import (
    IsOrganizationMember,
    IsOrganizationAdmin,
    IsOrganizationOwner,
)

User = get_user_model()


class OrganizationListCreateView(generics.ListCreateAPIView):
    """
    List all organizations the user belongs to, or create a new organization.
    """
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Strict isolation: Only return organizations the user is a member of
        return Organization.objects.filter(
            memberships__user=self.request.user,
            is_active=True,
        ).distinct()

    def perform_create(self, serializer):
        serializer.save()


class OrganizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a specific organization.
    """
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationMember]
    lookup_field = "id"

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user)

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ["PUT", "PATCH"]:
            if not IsOrganizationAdmin().has_object_permission(request, self, obj):
                raise PermissionDenied("Only organization Admins or Owners can update details.")
        elif request.method == "DELETE":
            if not IsOrganizationOwner().has_object_permission(request, self, obj):
                raise PermissionDenied("Only the organization Owner can delete the organization.")


class OrganizationMemberListCreateView(generics.ListCreateAPIView):
    """
    List members or add an existing user directly to the organization.
    """
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_organization(self):
        org_id = self.kwargs["org_id"]
        org = get_object_or_404(Organization, id=org_id)
        if not Membership.objects.filter(user=self.request.user, organization=org).exists():
            raise PermissionDenied("You are not a member of this organization.")
        return org

    def get_queryset(self):
        org = self.get_organization()
        return Membership.objects.filter(organization=org).select_related("user")

    def create(self, request, *args, **kwargs):
        org = self.get_organization()
        # Only Admins and Owners can add members directly
        if not Membership.objects.filter(
            user=request.user,
            organization=org,
            role__in=[MembershipRole.ADMIN, MembershipRole.OWNER],
        ).exists():
            raise PermissionDenied("Only Admins or Owners can add new members.")

        user_email = request.data.get("user_email")
        role = request.data.get("role", MembershipRole.MEMBER)

        if not user_email:
            raise ValidationError({"user_email": "This field is required."})

        try:
            target_user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            raise NotFound({"user_email": "User with this email was not found."})

        if Membership.objects.filter(user=target_user, organization=org).exists():
            raise ValidationError({"user_email": "User is already a member of this organization."})

        membership = Membership.objects.create(
            user=target_user,
            organization=org,
            role=role,
        )
        serializer = self.get_serializer(membership)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrganizationMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Update a member's role or remove a member from the organization.
    """
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        org_id = self.kwargs["org_id"]
        org = get_object_or_404(Organization, id=org_id)
        return Membership.objects.filter(organization=org)

    def perform_destroy(self, instance):
        # Only Owner or Admin can remove members; Owner cannot be removed
        org = instance.organization
        current_membership = get_object_or_404(Membership, user=self.request.user, organization=org)
        if current_membership.role not in [MembershipRole.ADMIN, MembershipRole.OWNER]:
            raise PermissionDenied("Insufficient permissions to remove members.")
        if instance.role == MembershipRole.OWNER:
            raise ValidationError("Organization Owner cannot be removed.")
        instance.delete()


class OrganizationInviteCreateView(views.APIView):
    """
    Create a secure invitation token for inviting team members by email.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=InvitationCreateSerializer,
        responses={201: OpenApiResponse(description="Invitation created successfully")},
    )
    def post(self, request, org_id):
        membership = get_object_or_404(
            Membership,
            organization_id=org_id,
            user=request.user,
            role__in=[MembershipRole.OWNER, MembershipRole.ADMIN],
        )

        serializer = InvitationCreateSerializer(
            data=request.data,
            context={"organization": membership.organization},
        )
        serializer.is_valid(raise_exception=True)

        invite = serializer.save(
            organization=membership.organization,
            invited_by=request.user,
        )

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
    """
    Accept an invitation using a secure token and join the organization.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=InvitationAcceptSerializer,
        responses={200: OpenApiResponse(description="Successfully joined organization")},
    )
    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        invite = get_object_or_404(Invitation, token=token, status=InvitationStatus.PENDING)

        if invite.is_expired:
            invite.status = InvitationStatus.REVOKED
            invite.save(update_fields=["status"])
            return Response(
                {"detail": "This invitation has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            membership, created = Membership.objects.get_or_create(
                organization=invite.organization,
                user=request.user,
                defaults={"role": invite.role},
            )
            if not created and membership.role != invite.role:
                membership.role = invite.role
                membership.save(update_fields=["role"])

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