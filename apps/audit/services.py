from typing import Optional, Dict, Any
from apps.audit.models import AuditLog, AuditAction
from apps.organizations.models import Organization


class AuditService:
    @staticmethod
    def log_event(
        organization: Organization,
        action: AuditAction,
        actor=None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        return AuditLog.objects.create(
            organization=organization,
            actor=actor,
            action=action,
            ip_address=ip_address,
            details=details or {},
        )