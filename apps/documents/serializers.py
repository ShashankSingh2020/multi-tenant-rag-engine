import os
from rest_framework import serializers
from apps.documents.models import Document

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md"}


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = (
            "id",
            "organization",
            "project",
            "title",
            "file",
            "file_type",
            "file_size_bytes",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organization",
            "project",
            "file_type",
            "file_size_bytes",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        )

    def validate_file(self, file_obj):
        ext = os.path.splitext(file_obj.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        # Max limit: 20MB
        if file_obj.size > 20 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 20MB.")
        return file_obj