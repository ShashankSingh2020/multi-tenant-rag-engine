import logging
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)


class TenantAIRateThrottle(SimpleRateThrottle):
    """
    Applies per-organization rate-limiting for high-compute AI endpoints.
    Identifies the tenant via user membership or falls back to IP address.
    """
    scope = "ai_query"
    rate = "30/minute"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            # Throttle keyed by tenant organization if available
            org_id = getattr(request.user, "organization_id", None)
            if not org_id and hasattr(request.user, "memberships"):
                membership = request.user.memberships.first()
                if membership:
                    org_id = membership.organization_id

            if org_id:
                return f"throttle_ai_{org_id}"
            return f"throttle_user_{request.user.id}"

        return self.get_ident(request)