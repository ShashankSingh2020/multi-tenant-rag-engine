from django.core.management.base import BaseCommand
from apps.subscriptions.models import SubscriptionPlan, PlanTier


class Command(BaseCommand):
    help = "Seeds default subscription plans for multi-tenant billing"

    def handle(self, *args, **options):
        plans = [
            {
                "name": PlanTier.FREE,
                "price_cents": 0,
                "max_ai_requests_per_month": 100,
                "max_documents": 5,
                "max_tokens_per_month": 50000,
            },
            {
                "name": PlanTier.PRO,
                "price_cents": 2900,  # $29.00
                "max_ai_requests_per_month": 2000,
                "max_documents": 100,
                "max_tokens_per_month": 1000000,
            },
            {
                "name": PlanTier.BUSINESS,
                "price_cents": 19900,  # $199.00
                "max_ai_requests_per_month": 50000,
                "max_documents": 5000,
                "max_tokens_per_month": 25000000,
            },
        ]

        for p_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=p_data["name"],
                defaults=p_data,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{action} plan: {plan.name}"))