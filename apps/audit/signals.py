import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.documents.models import Document
from apps.projects.models import Project
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Document)
def log_document_created(sender, instance, created, **kwargs):
    if created:
        try:
            AuditLog.objects.create(
                organization=instance.organization,
                action="DOCUMENT_UPLOADED",
                details={
                    "document_id": str(instance.id),
                    "title": instance.title,
                    "project_id": str(instance.project_id),
                    "file_size_bytes": instance.file_size_bytes,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record audit log for document creation: {e}")


@receiver(post_delete, sender=Document)
def log_document_deleted(sender, instance, **kwargs):
    try:
        AuditLog.objects.create(
            organization=instance.organization,
            action="DOCUMENT_DELETED",
            details={
                "document_id": str(instance.id),
                "title": instance.title,
                "project_id": str(instance.project_id),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to record audit log for document deletion: {e}")


@receiver(post_save, sender=Project)
def log_project_created(sender, instance, created, **kwargs):
    if created:
        try:
            AuditLog.objects.create(
                organization=instance.organization,
                action="PROJECT_CREATED",
                details={
                    "project_id": str(instance.id),
                    "name": instance.name,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record audit log for project creation: {e}")