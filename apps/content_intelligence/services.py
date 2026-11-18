import math
import re
from datetime import timedelta

from django.db import transaction

from apps.brands.services import ensure_strategy_version

from .models import ContentPlan, ContentPlanItem

OBJECTIVE_ORDER = ("reach", "authority", "conversion")
HOOKS = {
    "reach": "What most people overlook about {topic}",
    "authority": "A practical framework for making better decisions about {topic}",
    "conversion": "Ready to turn {topic} into measurable progress?",
}
FORMATS = {"reach": "carousel", "authority": "long-form text", "conversion": "case study"}


def _posts_per_week(posting_frequency):
    match = re.search(r"\d+", posting_frequency or "")
    return min(max(int(match.group()) if match else 3, 1), 14)


def _objective_sequence(total, strategy):
    weights = {
        "reach": strategy.reach_percentage,
        "authority": strategy.authority_percentage,
        "conversion": strategy.conversion_percentage,
    }
    raw = {key: total * value / 100 for key, value in weights.items()}
    counts = {key: math.floor(value) for key, value in raw.items()}
    remaining = total - sum(counts.values())
    ranked = sorted(OBJECTIVE_ORDER, key=lambda key: (raw[key] - counts[key], weights[key]), reverse=True)
    for key in ranked[:remaining]:
        counts[key] += 1

    sequence = []
    while len(sequence) < total:
        for key in sorted(OBJECTIVE_ORDER, key=lambda item: weights[item], reverse=True):
            if counts[key]:
                sequence.append(key)
                counts[key] -= 1
    return sequence


def _dates(start_date, days, total):
    if total == 1:
        return [start_date]
    return [start_date + timedelta(days=round(index * (days - 1) / (total - 1))) for index in range(total)]


def _terms(topic):
    words = [word.lower() for word in re.findall(r"[A-Za-zÀ-ÿ0-9]+", topic) if len(word) > 1]
    return list(dict.fromkeys(words))[:5]


@transaction.atomic
def create_content_plan(*, brand, cadence, start_date, user):
    """Create a deterministic editorial plan; never creates or schedules posts."""
    if cadence not in ContentPlan.Cadence.values:
        raise ValueError("Unsupported content plan cadence.")
    strategy, version = ensure_strategy_version(brand=brand, user=user)
    days = 7 if cadence == ContentPlan.Cadence.WEEKLY else 30
    total = _posts_per_week(brand.posting_frequency) * (1 if days == 7 else 4)
    objectives = _objective_sequence(total, strategy)
    pillars = brand.content_pillars or [brand.industry or brand.name]
    plan = ContentPlan(
        workspace=brand.workspace,
        brand=brand,
        strategy_version=version,
        cadence=cadence,
        start_date=start_date,
        end_date=start_date + timedelta(days=days - 1),
        created_by=user,
    )
    plan.full_clean()
    plan.save()
    planned_dates = _dates(start_date, days, total)
    items = []
    for index, objective in enumerate(objectives):
        pillar = pillars[index % len(pillars)]
        terms = _terms(pillar)
        cta = brand.cta_strategy or (
            "Invite the audience to share their experience."
            if objective != "conversion"
            else "Invite a relevant next step."
        )
        items.append(
            ContentPlanItem(
                plan=plan,
                position=index + 1,
                planned_for=planned_dates[index],
                objective=objective,
                topic=pillar,
                hook=HOOKS[objective].format(topic=pillar),
                cta=cta,
                keywords=terms,
                hashtags=[f"#{term.replace(' ', '')}" for term in terms],
                recommended_format=FORMATS[objective],
                recommended_platform="linkedin" if index % 2 == 0 else "instagram",
                content_pillar=pillar,
            )
        )
    ContentPlanItem.objects.bulk_create(items)
    return plan
