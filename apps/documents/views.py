from apps.documents.tasks import process_document_ingestion_task
import os
from django.db import transaction
from apps.audit.services import AuditService
from apps.audit.models import AuditAction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404

from apps.documents.models import Document
from apps.projects.models import Project
from apps.organizations.models import Membership
from apps.documents.serializers import DocumentSerializer
from apps.usage.services import UsageService


class DocumentListCreateView(generics.ListCreateAPIView):
    """
    List documents or upload a new file to a project.
    Validates organization subscription limits before saving.
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        project = get_object_or_404(Project, id=project_id)
        if not Membership.objects.filter(user=self.request.user, organization=project.organization).exists():
            raise PermissionDenied("You are not a member of the owning organization.")
        return Document.objects.filter(project=project)

    def create(self, request, *args, **kwargs):
        project_id = self.kwargs["project_id"]
        project = get_object_or_404(Project, id=project_id)
        org = project.organization

        if not Membership.objects.filter(user=request.user, organization=org).exists():
            raise PermissionDenied("You are not a member of the owning organization.")

        # Check Document Limit Quota
        usage = UsageService.get_organization_usage_summary(org)
        if usage["remaining_documents"] <= 0:
            raise ValidationError("Organization has reached its document storage quota. Upgrade plan to upload more.")

        file_obj = request.FILES.get("file")
        if not file_obj:
            raise ValidationError({"file": "No file uploaded."})

        ext = os.path.splitext(file_obj.name)[1].lower().replace(".", "")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = serializer.save(
            organization=org,
            project=project,
            file_type=ext,
            file_size_bytes=file_obj.size,
        )

        # Record upload in monthly usage
        UsageService.record_document_upload(org)
        # Record Audit Trail
        AuditService.log_event(
            organization=org,
            actor=request.user,
            action=AuditAction.DOCUMENT_UPLOADED,
            details={
                "document_id": str(document.id),
                "document_title": document.title,
                "file_type": ext,
                "project_id": str(project.id),
            },
        )

        # Trigger Celery asynchronous ingestion pipeline
        transaction.on_commit(lambda: process_document_ingestion_task.delay(str(document.id)))

        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Document.objects.filter(
            organization__memberships__user=self.request.user
        )