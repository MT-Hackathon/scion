from __future__ import annotations

import math
from datetime import datetime, timezone


DECAY_BY_REASON: dict[str, float] = {
    "methodological": 0.3,
    "calibrative": 0.1,
    "generative": 0.3,
    "cautionary": -0.1,
    "default": 0.5,
}


def base_level_activation(access_times: list[float], d: float = 0.5) -> float:
    """
    Compute ACT-R base-level activation.
    B = ln(sum(t_i^-d)), clamping each delta to 0.001.
    """
    if not access_times:
        return -999.0

    weighted_sum = 0.0
    for delta in access_times:
        safe_delta = max(float(delta), 0.001)
        weighted_sum += math.pow(safe_delta, -float(d))

    if weighted_sum <= 0.0:
        return -999.0
    return math.log(weighted_sum)


def decay_for_reason(reason: str | None) -> float:
    if not reason:
        return DECAY_BY_REASON["default"]
    return DECAY_BY_REASON.get(reason.lower(), DECAY_BY_REASON["default"])


def utility_score(
    activation: float,
    context_match: float,
    staleness: float,
    contradiction_count: int,
) -> float:
    raw = (
        (float(activation) * 0.6)
        + (float(context_match) * 0.8)
        - (float(staleness) * 0.4)
        - (int(contradiction_count) * 0.75)
    )
    return max(-10.0, min(10.0, raw))


def should_forget(utility: float, threshold: float = -2.0) -> bool:
    return float(utility) <= float(threshold)


def should_validate(
    last_validated: str | None,
    reason: str,
    max_days: int = 30,
) -> bool:
    if reason.lower() == "calibrative":
        return True
    if not last_validated:
        return True

    try:
        validated_at = datetime.fromisoformat(last_validated.replace("Z", "+00:00"))
    except ValueError:
        return True

    if validated_at.tzinfo is None:
        validated_at = validated_at.replace(tzinfo=timezone.utc)
    elapsed_days = (datetime.now(timezone.utc) - validated_at).days
    return elapsed_days >= int(max_days)

