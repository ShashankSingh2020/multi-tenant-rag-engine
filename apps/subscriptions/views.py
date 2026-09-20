from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.subscriptions.models import SubscriptionPlan, Subscription
from apps.organizations.models import Organization, Membership, MembershipRole
from apps.subscriptions.serializers import (
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
    ChangePlanSerializer,
)


class SubscriptionPlanListView(generics.ListAPIView):
    """
    List all available SaaS subscription plans and their quota limits.
    """
    queryset = SubscriptionPlan.objects.all().order_by("price_cents")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]


class CurrentSubscriptionView(APIView):
    """
    Get current subscription details for a specific organization.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="org_id", description="Organization UUID", required=True, type=str)
        ],
        responses={200: SubscriptionSerializer},
    )
    def get(self, request):
        org_id = request.query_params.get("org_id")
        if not org_id:
            raise ValidationError({"org_id": "Query parameter 'org_id' is required."})

        org = get_object_or_404(Organization, id=org_id)
        if not Membership.objects.filter(user=request.user, organization=org).exists():
            raise PermissionDenied("You are not a member of this organization.")

        subscription, _ = Subscription.objects.get_or_create(
            organization=org,
            defaults={"plan": SubscriptionPlan.objects.get(name="FREE")},
        )
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangeSubscriptionPlanView(APIView):
    """
    Simulate upgrading or downgrading an organization's subscription plan.
    (Only accessible by Organization OWNER).
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ChangePlanSerializer,
        responses={200: SubscriptionSerializer},
    )
    def post(self, request):
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = serializer.validated_data["organization_id"]
        plan_name = serializer.validated_data["plan_name"]

        org = get_object_or_404(Organization, id=org_id)

        # RBAC Check: Only OWNER can change the subscription
        membership = Membership.objects.filter(user=request.user, organization=org).first()
        if not membership or membership.role != MembershipRole.OWNER:
            raise PermissionDenied("Only the Organization Owner can modify the subscription tier.")

        new_plan = get_object_or_404(SubscriptionPlan, name=plan_name)

        subscription, _ = Subscription.objects.get_or_create(
            organization=org,
            defaults={"plan": new_plan},
        )
        subscription.plan = new_plan
        subscription.save()

        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_200_OK)