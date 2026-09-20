from django.db import models
from pgvector.django import VectorField, HnswIndex
from apps.common.models import TimeStampedUUIDModel
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.documents.models import Document


class DocumentChunk(TimeStampedUUIDModel):
    """
    Individual text chunk from a Document with pgvector embedding
    for semantic retrieval. Scoped to an organization and project.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="document_chunks",
        db_index=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="document_chunks",
        db_index=True,
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
        db_index=True,
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    class Meta:
        db_table = "document_chunks"
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        ordering = ["chunk_index"]
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            models.Index(fields=["organization", "project"]),
        ]

    def __str__(self):
        return f"{self.document.title} - Chunk #{self.chunk_index}"