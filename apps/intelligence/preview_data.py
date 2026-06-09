"""Example inputs + result payloads shown when an org is in preview
mode (not yet subscribed).

These render in each playground panel as a realistic demo: the input
fields are pre-filled and the result panels show what real output
looks like. Click the Submit button and the
``@intelligence_subscription_required`` decorator swaps the result
panel for the ``_subscribe_required.html`` paywall fragment.

Kept in its own module rather than inlined in ``views.py`` so the
view stays focused on request handling. Data shapes match the
``apps/api/serializers.py`` response schemas exactly, each example
goes through the same result partial that a real API response would.
"""

from __future__ import annotations

# Inputs pre-filled into form fields so the playground reads like a
# realistic walkthrough rather than an empty shell.
PREVIEW_INPUTS = {
    "score_packaging": {
        "title": "How I Built a $1M SaaS in 6 Months",
    },
    "score_video_hook": {
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    },
    "benchmark_channel": {
        "url": "https://youtube.com/@EconomicsExplained",
    },
    "benchmark_video": {
        "url": "https://www.youtube.com/watch?v=Nw1jHB4SMio",
    },
    "research_content_gaps": {
        # The combobox uses this as the pre-selected niche.
        "niche_slug": "python_programming_tutorials",
        "niche_name": "python programming tutorials",
    },
}


# Realistic API response payloads, each one passes through the
# corresponding ``_*_result.html`` partial as if it were a real call.
PREVIEW_RESULTS = {
    "score_packaging": {
        "score": 0.72,
        "percentile": 73,
        "raw_score": 0.7521,
        "mode": "title",
        "niche_slug": "entrepreneurship_business_growth",
        "niche_label": "entrepreneurship & business growth",
        "niche_confidence": 0.81,
    },
    "score_video_hook": {
        "score_id": "preview",
        "primary_archetype": "bold_claim",
        "secondary_archetype": "pattern_interrupt",
        "scores": {
            "clarity": 8,
            "specificity": 4,
            "tension": 6,
            "visual_energy": 7,
            "pace": 7,
        },
        "overall_score": 68,
        "transcript": "Ricky Gervais sollte unser aller Vorbild sein. I give a f*ck what you think.",
        "visual_summary": (
            "The host is speaking in a studio setting with dynamic text overlays "
            "appearing on screen in sync with his words, including the name "
            "'RICKY GERVAIS' and the phrase 'I GIVE A F*CK WHAT YOU THINK'."
        ),
        "strengths": [
            "The bold claim at second 0-2 immediately establishes a strong, opinionated stance.",
            "Dynamic text overlays from second 0-5 effectively reinforce the spoken message for viewers watching on mute.",
            "The transition to the English profanity at second 3 acts as a pattern interrupt that grabs attention.",
        ],
        "weaknesses": [
            "The claim that he should be a 'role model' is vague and lacks specific context or evidence at second 1.",
            "There is no clear curiosity gap or stake established; the viewer doesn't know why they should care about this specific opinion.",
            "The visual of the host is static, relying entirely on text overlays for energy.",
        ],
        "suggestions": [
            "Add a specific reason for the claim at second 2, such as 'because he never apologizes for his jokes'.",
            "Include a 1-second clip of a famous Ricky Gervais moment at second 4 to visually ground the bold claim.",
            "Add a specific question at second 5 to force viewer engagement, like 'Do you agree?'",
        ],
        "delta_vs_niche_top": -7,
        "key_differences_vs_top": [
            "Top hooks in this niche introduce specific stakes or a concrete 'why' within the first 4 seconds.",
            "High-performing clips often use a visual demonstration or a specific example rather than just a talking head with text.",
        ],
    },
    "benchmark_channel": {
        "channel": {
            "channel_id": "UCZ4AMrDcNrfy3X6nsU8-rPg",
            "title": "Economics Explained",
            "subscriber_count": 2_860_000,
            "video_count": 431,
            "engagement": {
                "view_to_sub_ratio": 0.1229,
                "like_to_view_ratio": 0.0298,
                "comment_to_view_ratio": 0.003,
            },
            "engagement_percentiles": {
                "view_to_sub_ratio": 50,
                "like_to_view_ratio": 50,
                "comment_to_view_ratio": 42,
                "overall": 47,
            },
            "sample_window_days": 60,
            "title_patterns": {
                "mean_length_chars": 40,
                "mean_length_words": 7,
                "share_with_question_mark": 0.30,
                "share_with_number": 0.10,
                "median_uppercase_ratio": 0.201,
                "share_with_emoji": 0.0,
            },
        },
        "niche": {
            "slug": "geopolitical_news_commentary",
            "name": "geopolitical news commentary",
            "match_score": 0.7561,
            "match_strength": "strong",
            "engagement": {
                "view_to_sub_ratio": {"p50": 0.122},
                "like_to_view_ratio": {"p50": 0.0295},
                "comment_to_view_ratio": {"p50": 0.0035},
            },
            "title_patterns": {
                "mean_length_chars": 66.52,
                "mean_length_words": 10.47,
                "share_with_question_mark": 0.0277,
                "share_with_number": 0.1318,
                "median_uppercase_ratio": 0.2059,
                "share_with_emoji": 0.0764,
                "common_niche_phrases": [
                    {"phrase": "trump s", "frequency": 0.0802, "used_by_channel": False},
                    {"phrase": "u s", "frequency": 0.0592, "used_by_channel": False},
                    {"phrase": "iran war", "frequency": 0.0458, "used_by_channel": True},
                    {"phrase": "white house", "frequency": 0.0325, "used_by_channel": False},
                    {"phrase": "of hormuz", "frequency": 0.0363, "used_by_channel": False},
                    {"phrase": "strait of", "frequency": 0.0344, "used_by_channel": False},
                ],
            },
            "exemplar_channels": [
                {"title": "60 Minutes", "subscriber_count": 0},
                {"title": "Middle East Eye", "subscriber_count": 3_730_000},
                {"title": "CBC News", "subscriber_count": 4_650_000},
                {"title": "Shawn Ryan Show", "subscriber_count": 0},
            ],
        },
    },
    "benchmark_video": {
        "video": {
            "video_id": "Nw1jHB4SMio",
            "title": "ÖRR am Tiefpunkt: Julia Ruhs gecancelt",
            "channel_title": "{ungeskriptet} by Ben",
            "published_at": "2025-09-20T07:59:00+00:00",
            "view_count": 598_823,
            "like_count": 18_044,
            "comment_count": 4_668,
            "engagement": {
                "view_to_sub_ratio": 0.631,
                "like_to_view_ratio": 0.0301,
                "comment_to_view_ratio": 0.0078,
            },
            "engagement_percentiles": {
                "view_to_sub_ratio": 96,
                "like_to_view_ratio": 59,
                "comment_to_view_ratio": 63,
                "overall": 73,
            },
            "title_patterns": {
                "length_chars": 38,
                "has_question": False,
                "has_number": False,
                "has_emoji": False,
                "fits_niche_patterns": False,
            },
        },
        "niche": {
            "slug": "uk_political_commentary",
            "name": "uk political commentary",
            "match_score": 0.7213,
            "match_strength": "moderate",
            "engagement": {
                "view_to_sub_ratio": {"p50": 0.0602},
                "like_to_view_ratio": {"p50": 0.0222},
                "comment_to_view_ratio": {"p50": 0.0050},
            },
            "title_patterns": {
                "mean_length_chars": 73.27,
                "mean_length_words": 11.76,
                "share_with_question_mark": 0.0425,
                "share_with_number": 0.1604,
                "median_uppercase_ratio": 0.1465,
                "share_with_emoji": 0.0472,
                "common_niche_phrases": [
                    {"phrase": "king charles", "frequency": 0.1038, "used_by_channel": False},
                    {"phrase": "prince harry", "frequency": 0.0519, "used_by_channel": False},
                    {"phrase": "keir starmer", "frequency": 0.0519, "used_by_channel": False},
                    {"phrase": "nigel farage", "frequency": 0.0283, "used_by_channel": False},
                ],
            },
        },
    },
    "research_content_gaps": {
        "niche": {"slug": "python_programming_tutorials", "name": "python programming tutorials"},
        "gaps": [
            {
                "canonical_title": "Python Tutorial for Beginners, Learn Python in 1 Hour",
                "opportunity_score": 68,
                "gap_type": "stale",
                "components": {"demand": 0.42, "supply": 0.08, "recency": 0.12},
                "explanation": (
                    "The top-ranking beginner tutorials predate Python 3.12 and "
                    "the rise of modern tooling (uv, ruff, pydantic v2, the "
                    "free-threaded interpreter in 3.13). They still teach "
                    "virtualenv + pip workflows that newcomers no longer see in "
                    "real codebases. A 2026-current refresher would land in a "
                    "market with high search demand and stale incumbents."
                ),
                "suggested_angles": [
                    "Modern Python in 2026: uv, ruff, and pydantic v2 from scratch",
                    "What actually changed in Python 3.12 and 3.13",
                    "Stop using virtualenv: the uv-first Python workflow",
                ],
                "evidence": {
                    "newest_quality_video_age_days": 412,
                    "trends_appearance_count": 6,
                    "autocomplete_rank": 1,
                    "residual_outlier_count": 2,
                    "top_competitors": [
                        {
                            "title": "Learn Python - Full Course for Beginners",
                            "channel_title": "freeCodeCamp.org",
                            "subscriber_count": 12_400_000,
                            "view_count": 41_200_000,
                            "age_days": 1820,
                        },
                        {
                            "title": "Python Tutorial - Python Full Course for Beginners",
                            "channel_title": "Programming with Mosh",
                            "subscriber_count": 4_510_000,
                            "view_count": 38_800_000,
                            "age_days": 1640,
                        },
                        {
                            "title": "Python for Beginners - Learn Python in 1 Hour",
                            "channel_title": "Programming with Mosh",
                            "subscriber_count": 4_510_000,
                            "view_count": 17_900_000,
                            "age_days": 1455,
                        },
                    ],
                    "related_queries": [],
                },
            },
            {
                "canonical_title": "Async Python: from callbacks to async/await",
                "opportunity_score": 52,
                "gap_type": "underserved",
                "components": {"demand": 0.31, "supply": 0.14, "recency": 0.38},
                "explanation": (
                    'Existing asyncio tutorials stop at "what is a coroutine" '
                    "without covering production patterns: TaskGroup, structured "
                    "concurrency, timeouts, and how to debug a hung event loop. "
                    "Search demand is steady and the few quality videos are "
                    "fragmented across blog-style explainers, not a single "
                    "go-to walkthrough."
                ),
                "suggested_angles": [
                    "Production asyncio: TaskGroup, timeouts, and structured concurrency",
                    "Async or threads? A decision guide for I/O-bound Python",
                    "Debugging a hung event loop: 3 patterns I wish I'd known",
                ],
                "evidence": {
                    "newest_quality_video_age_days": 184,
                    "trends_appearance_count": 4,
                    "autocomplete_rank": 3,
                    "residual_outlier_count": 1,
                    "top_competitors": [
                        {
                            "title": "AsyncIO in Python - Full Tutorial",
                            "channel_title": "Tech With Tim",
                            "subscriber_count": 1_850_000,
                            "view_count": 612_000,
                            "age_days": 730,
                        },
                        {
                            "title": "Understanding async/await in Python",
                            "channel_title": "ArjanCodes",
                            "subscriber_count": 412_000,
                            "view_count": 188_000,
                            "age_days": 540,
                        },
                    ],
                    "related_queries": [],
                },
            },
        ],
    },
    "list_niches": {
        "niches": [
            {"slug": "python_programming_tutorials", "name": "python programming tutorials", "gap_count": 76},
            {"slug": "data_science_career_roadmaps", "name": "data science career roadmaps", "gap_count": 40},
            {"slug": "full_stack_web_development", "name": "full stack web development", "gap_count": 51},
            {"slug": "devops_and_cloud_engineering", "name": "devops and cloud engineering", "gap_count": 44},
            {"slug": "ancient_history_documentaries", "name": "ancient history documentaries", "gap_count": 61},
            {"slug": "beginner_investment_strategies", "name": "beginner investment strategies", "gap_count": 66},
            {"slug": "personal_finance_budgeting", "name": "personal finance budgeting", "gap_count": 18},
            {"slug": "diy_woodworking_projects", "name": "diy woodworking projects", "gap_count": 81},
            {"slug": "homemade_bread_baking", "name": "homemade bread baking", "gap_count": 79},
            {"slug": "japan_travel_guides", "name": "japan travel guides", "gap_count": 72},
        ],
    },
}
