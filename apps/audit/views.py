from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from apps.organizations.models import Organization, Membership, MembershipRole
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    Retrieve audit history for an organization.
    Restricted to organization OWNER and ADMIN roles.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get("org_id")
        if not org_id:
            return AuditLog.objects.none()

        org = get_object_or_404(Organization, id=org_id)
        membership = Membership.objects.filter(user=self.request.user, organization=org).first()

        if not membership or membership.role not in [MembershipRole.OWNER, MembershipRole.ADMIN]:
            raise PermissionDenied("Only organization owners and admins can view compliance audit trails.")

        return AuditLog.objects.filter(organization=org)