from django.contrib import admin
from apps.documents.models import Document, DocumentChunk


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    fields = ("chunk_index", "token_count")
    readonly_fields = ("chunk_index", "token_count")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "organization", "status", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("title", "project__name", "organization__name")
    inlines = [DocumentChunkInline]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "token_count")
    search_fields = ("document__title", "content")