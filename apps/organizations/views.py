from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.organizations.models import Organization, Membership, MembershipRole
from apps.organizations.serializers import OrganizationSerializer, MembershipSerializer
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
    List members or add a new member to the organization.
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
        # Only Admins and Owners can add members
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