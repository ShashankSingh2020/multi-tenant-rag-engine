from rest_framework import permissions
from apps.organizations.models import Membership, MembershipRole


class IsOrganizationMember(permissions.BasePermission):
    """
    Allows access if the user is an active member of the target organization.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Support both direct Organization instances or tenant-owned objects
        org = obj if hasattr(obj, "slug") else getattr(obj, "organization", None)
        if not org:
            return False

        return Membership.objects.filter(
            user=request.user,
            organization=org,
        ).exists()


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Allows access only to Organization Admins or Owners.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        org = obj if hasattr(obj, "slug") else getattr(obj, "organization", None)
        if not org:
            return False

        return Membership.objects.filter(
            user=request.user,
            organization=org,
            role__in=[MembershipRole.ADMIN, MembershipRole.OWNER],
        ).exists()


class IsOrganizationOwner(permissions.BasePermission):
    """
    Allows access exclusively to the Organization Owner.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        org = obj if hasattr(obj, "slug") else getattr(obj, "organization", None)
        if not org:
            return False

        return Membership.objects.filter(
            user=request.user,
            organization=org,
            role=MembershipRole.OWNER,
        ).exists()