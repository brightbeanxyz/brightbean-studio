"""Trial Reel settings shared by both Instagram login paths."""

from .exceptions import PublishError
from .types import PostType, PublishContent

TRIAL_STRATEGY_KEY = "trial_reel_graduation_strategy"
TRIAL_STRATEGIES = ("MANUAL", "SS_PERFORMANCE")


def trial_reel_error(extra: dict, *, single_video: bool) -> str:
    strategy = extra.get(TRIAL_STRATEGY_KEY)
    if strategy is None:
        return ""
    if strategy not in TRIAL_STRATEGIES:
        return "Choose a valid Instagram Trial Reel sharing mode."
    if not single_video or extra.get("post_type") == "story":
        return "An Instagram Trial Reel needs exactly one video and cannot be a Story or carousel."
    return ""


def trial_params(content: PublishContent, platform: str) -> dict | None:
    error = trial_reel_error(
        {**content.extra, "post_type": content.post_type.value},
        single_video=len(content.media_urls) == 1
        and content.is_video(0)
        and content.post_type not in (PostType.STORY, PostType.CAROUSEL),
    )
    if error:
        raise PublishError(error, platform=platform, retryable=False)
    strategy = content.extra.get(TRIAL_STRATEGY_KEY)
    return {"graduation_strategy": strategy} if strategy is not None else None
