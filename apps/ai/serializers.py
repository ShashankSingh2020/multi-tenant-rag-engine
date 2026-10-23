from rest_framework import serializers

class AIQuerySerializer(serializers.Serializer):
    project_id = serializers.UUIDField(required=True)
    query = serializers.CharField(required=False)
    prompt = serializers.CharField(required=False)
    chat_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)

    def validate(self, attrs):
        query_text = attrs.get("query") or attrs.get("prompt")
        if not query_text:
            raise serializers.ValidationError({"query": "A query or prompt is required."})
        attrs["query_text"] = query_text
        return attrs
