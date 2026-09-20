import sys
from django.db import models
from apps.common.models import TimeStampedUUIDModel
from apps.organizations.models import Organization
from apps.projects.models import Project
from apps.documents.models import Document
from pgvector.django import VectorField

# Module-level index configuration (safe from nested class scope issues)
_chunk_indexes = []
if "pytest" not in sys.modules and "test" not in sys.argv:
    from pgvector.django import HnswIndex
    _chunk_indexes = [
        HnswIndex(
            name="chunk_embedding_hnsw_idx",
            fields=["embedding"],
            m=16,
            ef_construction=64,
            opclasses=["vector_cosine_ops"],
        ),
    ]


class DocumentChunk(TimeStampedUUIDModel):
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
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()
    token_count = models.PositiveIntegerField(default=0)
    embedding = VectorField(dimensions=768)

    class Meta:
        db_table = "document_chunks"
        indexes = _chunk_indexes

    def __str__(self):
        return f"{self.document.title} - Chunk #{self.chunk_index}"