from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from apps.organizations.models import Organization, Membership
from apps.projects.models import Project
from apps.projects.serializers import ProjectSerializer
from apps.audit.services import AuditService
from apps.audit.models import AuditAction


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_orgs = Organization.objects.filter(memberships__user=self.request.user)
        return Project.objects.filter(organization__in=user_orgs)

    def perform_create(self, serializer):
        org_id = self.request.query_params.get("org_id") or self.request.data.get("organization")
        if not org_id:
            raise ValidationError({"organization": "Organization ID is required to create a project."})

        org = get_object_or_404(Organization, id=org_id)
        if not Membership.objects.filter(user=self.request.user, organization=org).exists():
            raise PermissionDenied("You are not a member of this organization.")

        project = serializer.save(organization=org)

        # Audit Logging
        AuditService.log_event(
            organization=org,
            actor=self.request.user,
            action=AuditAction.PROJECT_CREATED,
            details={"project_id": str(project.id), "project_name": project.name},
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_orgs = Organization.objects.filter(memberships__user=self.request.user)
        return Project.objects.filter(organization__in=user_orgs)