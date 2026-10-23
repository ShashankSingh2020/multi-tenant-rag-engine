from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from apps.projects.models import Project
from apps.organizations.models import Membership, MembershipRole
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.usage.services import UsageService
from apps.documents.tasks import process_document_ingestion_task


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        return Document.objects.filter(
            project_id=project_id,
            organization__memberships__user=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        project_id = self.kwargs["project_id"]
        project = get_object_or_404(Project, id=project_id)
        org = project.organization

        if not Membership.objects.filter(user=request.user, organization=org).exists():
            raise PermissionDenied("You are not a member of the owning organization.")

        usage = UsageService.get_organization_usage_summary(org)
        if usage.get("remaining_documents", 0) <= 0:
            raise ValidationError("Organization document quota exceeded. Limit reached.")

        file_obj = request.FILES.get("file")
        if not file_obj:
            raise ValidationError({"file": "No file uploaded."})

        ext = file_obj.name.lower().split(".")[-1]
        if ext not in ["txt", "pdf", "docx"]:
            raise ValidationError({"file": f"File extension .{ext} is not allowed. Supported: txt, pdf, docx."})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        concrete_field_names = [f.name for f in Document._meta.concrete_fields]
        save_kwargs = {
            "project": project,
            "organization": org,
            "file_type": ext,
            "title": request.data.get("title") or file_obj.name,
        }
        if "uploaded_by" in concrete_field_names:
            save_kwargs["uploaded_by"] = request.user
        elif "user" in concrete_field_names:
            save_kwargs["user"] = request.user

        doc = serializer.save(**save_kwargs)

        UsageService.record_document_upload(org.id)
        process_document_ingestion_task.delay(str(doc.id))

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Document.objects.filter(organization__memberships__user=self.request.user)

    def perform_destroy(self, instance):
        membership = Membership.objects.filter(
            organization=instance.organization,
            user=self.request.user,
        ).first()
        if not membership or membership.role not in [MembershipRole.ADMIN, MembershipRole.OWNER]:
            raise PermissionDenied("Only organization Admins and Owners can delete documents.")
        instance.delete()
