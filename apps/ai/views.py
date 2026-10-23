from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from apps.projects.models import Project
from apps.organizations.models import Membership
from apps.usage.services import UsageService
from apps.ai.services import AIService
from apps.ai.serializers import AIQuerySerializer
from apps.audit.models import AuditLog


class AIQueryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if "project_id" in kwargs and "project_id" not in data:
            data["project_id"] = kwargs["project_id"]

        serializer = AIQuerySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        project_id = validated["project_id"]
        query_text = validated["query_text"]
        chat_history = validated.get("chat_history", [])
        top_k = validated.get("top_k", 5)

        project = get_object_or_404(Project, id=project_id)
        org = project.organization

        if not Membership.objects.filter(user=request.user, organization=org).exists():
            raise PermissionDenied("You are not authorized to query this project.")

        # Pre-flight quota check
        UsageService.check_quota(organization_id=org.id, feature="ai_requests", increment=1)

        try:
            result = AIService.query_rag(
                project_id=project.id,
                organization_id=org.id,
                query_text=query_text,
                user=request.user,
                chat_history=chat_history,
                top_k=top_k,
            )
        except Exception as err:
            return Response(
                {"error": "AI provider service error", "detail": str(err)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Audit AI Query event
        AuditLog.objects.create(
            organization=org,
            actor=request.user,
            action="AI_QUERY",
        )

        return Response(result, status=status.HTTP_200_OK)


RAGQueryView = AIQueryView
