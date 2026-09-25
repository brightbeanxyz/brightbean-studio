from apps.analytics.derive import calculate_engagement_rate, derive, engagement_denominator, engagement_rate


def test_calculate_engagement_rate_cases():
    assert calculate_engagement_rate(20, views=100, reach=50) == 20.0
    assert calculate_engagement_rate(20, views=0, reach=200) == 10.0
    assert calculate_engagement_rate(20, views=0, reach=0) == 0
    assert calculate_engagement_rate(0, views=100, reach=100) == 0


def test_engagement_rate_prefers_views_denominator():
    metric = engagement_rate(
        {
            "views": [100],
            "reach": [50],
            "reactions": [20],
        },
        days=1,
    )

    assert metric.value == 20.0


def test_engagement_rate_falls_back_to_reach_when_views_are_zero():
    metric = engagement_rate(
        {
            "views": [0],
            "reach": [200],
            "reactions": [20],
        },
        days=1,
    )

    assert metric.value == 10.0


def test_engagement_rate_returns_zero_without_denominator():
    metric = engagement_rate(
        {
            "views": [0],
            "reach": [0],
            "reactions": [20],
            "clicks": [4],
        },
        days=1,
    )

    assert metric.value == 0.0
    assert metric.series == [0.0]


def test_engagement_rate_returns_zero_without_engagements():
    metric = engagement_rate(
        {
            "views": [100],
            "reach": [100],
            "reactions": [0],
        },
        days=1,
    )

    assert metric.value == 0.0


def test_derive_marks_rates_and_minutes_as_our_daily_average():
    """Percent and minutes cards show our average of the daily figures, which
    the dashboard has to label as calculated by us, not the platform."""
    assert derive([10.0, 20.0], days=2, kind="percent").averaged is True
    assert derive([10.0, 20.0], days=2, kind="minutes").averaged is True
    assert derive([10.0, 20.0], days=2, kind="count").averaged is False


def test_engagement_denominator_matches_what_the_rate_divides_by():
    series = {"views": [0, 0], "reach": [0, 40], "likes": [0, 4]}

    assert engagement_denominator(series, days=1) == "reach"
    assert engagement_denominator({"likes": [4]}, days=1) is None
