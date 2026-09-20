from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.organizations.models import Organization, Membership
from apps.usage.services import UsageService


class OrganizationUsageView(APIView):
    """
    Inspect real-time quota allowances vs actual monthly consumption.
    Accessible by all active members of the organization.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="org_id", description="Organization UUID", required=True, type=str)
        ],
        responses={200: dict},
    )
    def get(self, request):
        org_id = request.query_params.get("org_id")
        if not org_id:
            raise ValidationError({"org_id": "Query parameter 'org_id' is required."})

        org = get_object_or_404(Organization, id=org_id)
        if not Membership.objects.filter(user=request.user, organization=org).exists():
            raise PermissionDenied("You are not a member of this organization.")

        usage_summary = UsageService.get_organization_usage_summary(org)
        return Response(usage_summary, status=status.HTTP_200_OK)