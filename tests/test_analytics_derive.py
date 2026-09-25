from apps.analytics.derive import calculate_engagement_rate, derive, engagement_rate


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


def test_derive_averages_a_rate_over_the_days_with_data_only():
    """A zero-filled day with no data yet is not a 0% day."""
    metric = derive([50.0, 50.0, 0.0, 0.0], days=4, kind="percent", present=[True, True, False, False])

    assert metric.value == 50.0


def test_derive_ends_a_daily_quantity_at_the_last_reported_day():
    """A quiet day inside the window is a real 0 minutes; the days after the last
    report (YouTube Analytics lags 2-3 days) have not arrived yet."""
    metric = derive([30.0, 0.0, 30.0, 0.0, 0.0], days=5, kind="minutes", present=[True, False, True, False, False])

    assert metric.value == 20.0


def test_derive_without_a_presence_mask_averages_every_day():
    assert derive([30.0, 0.0], days=2, kind="minutes").value == 15.0


def test_derive_carries_the_estimated_flag():
    assert derive([1.0], days=1, kind="count", estimated=True).estimated is True
    assert derive([1.0], days=1, kind="count").estimated is False


def test_engagement_rate_reports_the_denominator_it_used():
    assert engagement_rate({"views": [0, 0], "reach": [0, 40], "likes": [0, 4]}, days=1).denominator == "reach"
    assert engagement_rate({"likes": [4]}, days=1, fallback_followers=200).denominator == "followers"
    assert engagement_rate({"likes": [4]}, days=1).denominator is None


def test_engagement_rate_sparkline_divides_by_the_headline_denominator():
    """The card names one denominator, so every sparkline day must use it too,
    even when another denominator has data that day."""
    metric = engagement_rate({"views": [100, 0], "reach": [50, 50], "likes": [10, 10]}, days=2)

    assert metric.denominator == "views"
    assert metric.series == [10.0, 0.0]


def test_engagement_rate_sparkline_on_the_follower_fallback_is_a_rate():
    metric = engagement_rate({"likes": [5, 10]}, days=2, fallback_followers=100)

    assert metric.value == 15.0
    assert metric.series == [5.0, 10.0]


def test_derive_series_shows_unreported_days_as_gaps_matching_the_average():
    """The sparkline must agree with the value: a day the average skipped is
    drawn as a gap (None), not as a drop to 0."""
    rate = derive([50.0, 0.0, 50.0, 0.0], days=4, kind="percent", present=[True, False, True, False])
    minutes = derive([30.0, 0.0, 30.0, 0.0], days=4, kind="minutes", present=[True, False, True, False])
    views = derive([10.0, 0.0, 10.0, 0.0], days=4, kind="count", present=[True, False, True, False])

    assert rate.series == [50.0, None, 50.0, None]
    # A quiet day inside the window is a real 0; only the trailing run is unreported.
    assert minutes.series == [30.0, 0.0, 30.0, None]
    assert views.series == [10.0, 0.0, 10.0, None]
    assert views.value == 20.0


def test_engagement_rate_sparkline_leaves_unreported_days_as_gaps():
    series = {"views": [100.0, 100.0, 0.0], "likes": [10.0, 5.0, 0.0]}
    present = {"views": [True, True, False], "likes": [True, True, False]}

    metric = engagement_rate(series, days=3, present_by_metric=present)

    assert metric.series == [10.0, 5.0, None]
    assert metric.value == 7.5
