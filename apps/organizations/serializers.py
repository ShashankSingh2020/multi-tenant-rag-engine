import uuid
from rest_framework import serializers
from django.utils.text import slugify
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.organizations.models import (
    Organization,
    Membership,
    MembershipRole,
    Invitation,
    InvitationStatus,
)
from apps.accounts.serializers import UserSerializer
from apps.subscriptions.models import Subscription, SubscriptionPlan, PlanTier

User = get_user_model()


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = Membership
        fields = ("id", "user", "user_email", "role", "created_at")
        read_only_fields = ("id", "created_at", "user")

    def validate_role(self, value):
        if value not in MembershipRole.values:
            raise serializers.ValidationError("Invalid role specified.")
        return value


class OrganizationSerializer(serializers.ModelSerializer):
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "slug",
            "is_active",
            "created_at",
            "updated_at",
            "current_user_role",
        )
        read_only_fields = (
            "id",
            "slug",
            "is_active",
            "created_at",
            "updated_at",
            "current_user_role",
        )

    def get_current_user_role(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            membership = Membership.objects.filter(
                user=request.user, organization=obj
            ).first()
            return membership.role if membership else None
        return None

    def create(self, validated_data):
        user = self.context["request"].user
        name = validated_data["name"]

        base_slug = slugify(name) or "org"
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        with transaction.atomic():
            org = Organization.objects.create(
                name=name,
                slug=slug,
                is_active=True,
            )
            # Creator becomes OWNER
            Membership.objects.create(
                user=user,
                organization=org,
                role=MembershipRole.OWNER,
            )
            # Provision baseline FREE subscription plan
            free_plan, _ = SubscriptionPlan.objects.get_or_create(
                name=PlanTier.FREE,
                defaults={
                    "max_ai_requests_per_month": 100,
                    "max_documents": 10,
                    "max_tokens_per_month": 50000,
                    "price_cents": 0,
                },
            )
            Subscription.objects.create(
                organization=org,
                plan=free_plan,
            )

        return org


class InvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ("id", "email", "role", "created_at", "expires_at")
        read_only_fields = ("id", "created_at", "expires_at")

    def validate_role(self, value):
        if value not in MembershipRole.values:
            raise serializers.ValidationError("Invalid role specified.")
        return value

    def validate_email(self, value):
        org = self.context["organization"]
        clean_email = value.lower().strip()

        # Check if already an existing member in this organization
        if Membership.objects.filter(
            organization=org, user__email__iexact=clean_email
        ).exists():
            raise serializers.ValidationError(
                "A user with this email is already a member of this organization."
            )

        # Check if a pending invite already exists for this email
        if Invitation.objects.filter(
            organization=org,
            email__iexact=clean_email,
            status=InvitationStatus.PENDING,
        ).exists():
            raise serializers.ValidationError(
                "A pending invitation already exists for this email."
            )

        return clean_email


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, trim_whitespace=True)