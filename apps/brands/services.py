from django.db import transaction
from django.db.models import Max

from .models import EditorialStrategy, EditorialStrategyVersion


@transaction.atomic
def save_editorial_strategy(*, brand, data, user):
    """Persist the current strategy and an immutable, monotonic snapshot."""
    strategy, _ = EditorialStrategy.objects.select_for_update().get_or_create(brand=brand)
    strategy.reach_percentage = data["reach_percentage"]
    strategy.authority_percentage = data["authority_percentage"]
    strategy.conversion_percentage = data["conversion_percentage"]
    strategy.full_clean()
    strategy.save()

    latest = strategy.versions.aggregate(latest=Max("version"))["latest"] or 0
    version = EditorialStrategyVersion(
        strategy=strategy,
        version=latest + 1,
        reach_percentage=strategy.reach_percentage,
        authority_percentage=strategy.authority_percentage,
        conversion_percentage=strategy.conversion_percentage,
        created_by=user,
    )
    version.full_clean()
    version.save()
    return strategy, version


@transaction.atomic
def ensure_strategy_version(*, brand, user=None):
    strategy, _ = EditorialStrategy.objects.get_or_create(brand=brand)
    version = strategy.versions.first()
    if version is None:
        _, version = save_editorial_strategy(
            brand=brand,
            data={"reach_percentage": 35, "authority_percentage": 50, "conversion_percentage": 15},
            user=user,
        )
    return strategy, version
