from rest_framework import serializers
from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "organization", "name", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def validate_name(self, value):
        org = self.context.get("organization") or getattr(self.instance, "organization", None)
        if org and Project.objects.filter(organization=org, name=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("A project with this name already exists in this organization.")
        return value