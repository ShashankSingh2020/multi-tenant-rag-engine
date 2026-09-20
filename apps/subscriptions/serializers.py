from rest_framework import serializers
from apps.subscriptions.models import SubscriptionPlan, Subscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "name",
            "max_ai_requests_per_month",
            "max_documents",
            "max_tokens_per_month",
            "price_cents",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "organization",
            "plan",
            "is_active",
            "current_period_start",
            "current_period_end",
        )


class ChangePlanSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField(required=True)
    plan_name = serializers.ChoiceField(choices=["FREE", "PRO", "BUSINESS"], required=True)