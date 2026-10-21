from rest_framework import views, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.organizations.models import Organization, Membership
from apps.usage.services import get_active_usage_record


class UsageSummaryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        org_id = request.query_params.get("organization")
        if not org_id:
            return Response({"error": "organization query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        org = get_object_or_404(Organization, id=org_id)
        if not Membership.objects.filter(user=request.user, organization=org).exists():
            return Response({"error": "Unauthorized access to organization"}, status=status.HTTP_403_FORBIDDEN)

        usage = get_active_usage_record(org_id)
        sub = getattr(org, "subscription", None)
        plan = getattr(sub, "plan", None)

        return Response({
            "plan_name": plan.name if plan else "Free",
            "ai_requests_used": usage.ai_requests_count,
            "max_ai_requests": plan.max_ai_requests_per_month if plan else 100,
            "tokens_used": usage.total_tokens_used,
            "max_tokens": plan.max_tokens_per_month if plan else 50000,
            "documents_count": usage.documents_uploaded_count,
            "max_documents": plan.max_documents if plan else 10,
        })
