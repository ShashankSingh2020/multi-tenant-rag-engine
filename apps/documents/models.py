import os
from django.db import models
from apps.common.models import TimeStampedUUIDModel
from apps.organizations.models import Organization
from apps.projects.models import Project


def tenant_document_upload_path(instance, filename):
    return f"tenants/{instance.organization.id}/projects/{instance.project.id}/docs/{filename}"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    READY = "READY", "Ready"
    FAILED = "FAILED", "Failed"


class Document(TimeStampedUUIDModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=tenant_document_upload_path, max_length=512)
    file_type = models.CharField(max_length=50, blank=True)
    file_size_bytes = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "documents"
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"

# Expose DocumentChunk in the documents model registry
from apps.documents.chunk_models import DocumentChunk