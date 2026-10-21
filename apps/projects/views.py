from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from apps.organizations.models import Organization, Membership
from apps.projects.models import Project
from apps.projects.serializers import ProjectSerializer


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Project.objects.filter(
            organization__memberships__user=self.request.user
        ).distinct()
        org_id = self.request.query_params.get("organization")
        if org_id:
            qs = qs.filter(organization_id=org_id)
        return qs

    def perform_create(self, serializer):
        org_id = self.request.data.get("organization")
        if not org_id:
            raise ValidationError({"organization": "Organization is required."})

        org = get_object_or_404(Organization, id=org_id)
        if not Membership.objects.filter(user=self.request.user, organization=org).exists():
            raise PermissionDenied("You are not a member of this organization.")

        try:
            serializer.save(organization=org)
        except IntegrityError:
            raise ValidationError({"name": "A project with this name already exists in this organization."})


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_object(self):
        # Support both 'pk' and 'id' url kwargs from urls.py
        lookup_val = self.kwargs.get("id") or self.kwargs.get("pk")
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset, id=lookup_val)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        return Project.objects.filter(organization__memberships__user=self.request.user).distinct()
