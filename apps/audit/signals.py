from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from apps.audit.models import AuditLog
from apps.documents.models import Document
from apps.projects.models import Project


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip_addr = "127.0.0.1"
    if request:
        ip_addr = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "127.0.0.1"
        ip_addr = ip_addr.split(",")[0].strip()

    AuditLog.objects.create(
        actor=user,
        action="AUTH_LOGIN",
        ip_address=ip_addr,
    )


@receiver(post_save, sender=Document)
def log_document_created(sender, instance, created, **kwargs):
    if created and instance.organization:
        AuditLog.objects.create(
            organization=instance.organization,
            actor=getattr(instance, "uploaded_by", None),
            action="DOCUMENT_UPLOAD",
        )


@receiver(post_save, sender=Project)
def log_project_created(sender, instance, created, **kwargs):
    if created and instance.organization:
        AuditLog.objects.create(
            organization=instance.organization,
            action="PROJECT_CREATED",
        )
