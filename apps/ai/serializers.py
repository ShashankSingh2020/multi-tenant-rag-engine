from rest_framework import serializers


class RAGQueryRequestSerializer(serializers.Serializer):
    project_id = serializers.UUIDField(required=True)
    query = serializers.CharField(required=True, min_length=3, max_length=1000)
    top_k = serializers.IntegerField(required=False, default=4, min_value=1, max_value=10)


class SourceChunkSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    document_title = serializers.CharField()
    chunk_index = serializers.IntegerField()
    relevance_score = serializers.FloatField()
    snippet = serializers.CharField()


class RAGQueryResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    answer = serializers.CharField()
    sources = SourceChunkSerializer(many=True)
    tokens_consumed = serializers.IntegerField()