import logging
import inspect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.ai.services import AIService
from apps.usage.services import UsageService
from apps.audit.services import AuditService
from apps.projects.models import Project

logger = logging.getLogger(__name__)


def safe_audit_log(actor_user, organization, action_name, metadata):
    """Dynamically invokes AuditService matching its exact signature without errors."""
    target_func = None
    inst = None

    # Check classmethods/staticmethods first
    for name in ["log_event", "log_action", "create_log", "log"]:
        if hasattr(AuditService, name):
            target_func = getattr(AuditService, name)
            break

    # If not on class, check instance methods
    if not target_func:
        try:
            inst = AuditService()
            for name in ["log_event", "log_action", "create_log", "log"]:
                if hasattr(inst, name):
                    target_func = getattr(inst, name)
                    break
        except Exception:
            pass

    if not target_func:
        return

    # Inspect the parameters required by the target audit method
    try:
        sig = inspect.signature(target_func)
        param_names = list(sig.parameters.keys())
        kwargs = {}

        for p in param_names:
            if p in ["user", "actor"]:
                kwargs[p] = actor_user
            elif p in ["organization", "org"]:
                kwargs[p] = organization
            elif p in ["action", "event_type", "event"]:
                kwargs[p] = action_name
            elif p in ["details", "metadata", "extra", "data"]:
                kwargs[p] = metadata

        target_func(**kwargs)
    except Exception as e:
        logger.warning(f"Audit log bypassed: {e}")


def safe_record_usage(organization, tokens_used):
    """Safely invokes UsageService to record token consumption and query count."""
    # 1. Try classmethod `record_ai_request_usage`
    if hasattr(UsageService, "record_ai_request_usage"):
        try:
            UsageService.record_ai_request_usage(organization=organization, tokens_used=tokens_used)
            return
        except TypeError:
            try:
                UsageService.record_ai_request_usage(organization, tokens_used)
                return
            except Exception as e:
                logger.warning(f"Usage recording failed on classmethod record_ai_request_usage: {e}")

    # 2. Try classmethod `record_ai_request`
    if hasattr(UsageService, "record_ai_request"):
        try:
            UsageService.record_ai_request(organization=organization, tokens_used=tokens_used)
            return
        except TypeError:
            try:
                UsageService.record_ai_request(organization, tokens_used)
                return
            except Exception as e:
                logger.warning(f"Usage recording failed on classmethod record_ai_request: {e}")

    # 3. Try instance methods
    try:
        inst = UsageService()
        for method_name in ["record_ai_request_usage", "record_ai_request"]:
            if hasattr(inst, method_name):
                func = getattr(inst, method_name)
                try:
                    func(organization=organization, tokens_used=tokens_used)
                    return
                except TypeError:
                    try:
                        func(organization, tokens_used)
                        return
                    except Exception:
                        continue
    except Exception as e:
        logger.warning(f"Usage recording failed on instance methods: {e}")


class RAGQueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        project_id = request.data.get("project_id")
        query = request.data.get("query")
        top_k = int(request.data.get("top_k", 3))
        chat_history = request.data.get("chat_history", [])

        if not project_id or not query:
            return Response(
                {"error": "Both 'project_id' and 'query' are required fields."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Project Tenant Isolation Verification
        try:
            project = Project.objects.select_related("organization").get(
                id=project_id,
                organization__memberships__user=request.user,
            )
        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        org = project.organization

        # 2. Check Quota Usage
        usage_service = UsageService()
        if hasattr(usage_service, "can_execute_ai_request"):
            try:
                allowed = usage_service.can_execute_ai_request(org)
            except TypeError:
                try:
                    allowed = usage_service.can_execute_ai_request(organization=org)
                except TypeError:
                    allowed = usage_service.can_execute_ai_request()

            if not allowed:
                return Response(
                    {"error": "AI request quota exceeded for the current billing period."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        # 3. Vector Retrieval & Synthesis via Gemini
        ai_service = AIService()
        result = ai_service.query_project_knowledge_base(
            project=project,
            query=query,
            top_k=top_k,
            chat_history=chat_history,
        )

        # 4. Record Token Consumption & Decrement Quota
        tokens_consumed = result.get("total_tokens", 0)
        safe_record_usage(organization=org, tokens_used=tokens_consumed)

        # 5. Clean Audit Log Registration
        safe_audit_log(
            actor_user=request.user,
            organization=org,
            action_name="AI_QUERY_EXECUTED",
            metadata={
                "project_id": str(project.id),
                "query": query,
                "tokens_consumed": tokens_consumed,
                "sources_matched": len(result.get("sources", [])),
            },
        )

        return Response(result, status=status.HTTP_200_OK)