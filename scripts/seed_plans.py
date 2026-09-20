from apps.subscriptions.models import SubscriptionPlan, PlanTier


def run():
    plans = [
        {
            "name": PlanTier.FREE,
            "max_ai_requests_per_month": 100,
            "max_documents": 10,
            "max_tokens_per_month": 50000,
            "price_cents": 0,
        },
        {
            "name": PlanTier.PRO,
            "max_ai_requests_per_month": 2000,
            "max_documents": 100,
            "max_tokens_per_month": 1000000,
            "price_cents": 2900,  # $29/mo
        },
        {
            "name": PlanTier.BUSINESS,
            "max_ai_requests_per_month": 10000,
            "max_documents": 1000,
            "max_tokens_per_month": 5000000,
            "price_cents": 9900,  # $99/mo
        },
    ]

    for plan_data in plans:
        obj, created = SubscriptionPlan.objects.update_or_create(
            name=plan_data["name"],
            defaults=plan_data,
        )
        action = "Created" if created else "Updated"
        print(f"{action} plan: {obj.name}")


if __name__ == "__main__":
    run()