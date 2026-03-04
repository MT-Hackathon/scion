from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


CHARACTERS = (
    "exploratory",
    "corrective",
    "deepening",
    "integrative",
    "reductive",
    "forced",
)


@dataclass(slots=True)
class EpisodeFeatures:
    total_events: int
    tool_calls: int
    tool_results: int
    user_messages: int
    agent_reasoning: int
    corrections: int
    error_signatures: int
    git_commits: int
    unique_artifacts: int
    repeated_artifact_ratio: float
    correction_ratio: float
    error_ratio: float
    reasoning_ratio: float
    git_ratio: float
    artifact_diversity: float
    dominant_scope_key: str | None
    dominant_event_type: str | None
    dominant_action: str | None


def _strip_line_suffix(path: str) -> str:
    if ":" not in path:
        return path
    base, suffix = path.rsplit(":", 1)
    if suffix.replace("-", "").isdigit():
        return base
    return path


def _scope_key_from_artifact(artifact_key: str) -> str:
    cleaned = _strip_line_suffix(artifact_key)
    if not cleaned:
        return cleaned
    path = PurePosixPath(cleaned)
    if path.suffix:
        parent = path.parent.as_posix()
        return parent if parent and parent != "." else cleaned
    return cleaned


def _dominant_scope_key(events: list[dict[str, Any]]) -> str | None:
    scope_counter: Counter[str] = Counter()
    for event in events:
        artifact_key = event.get("artifact_key")
        if not artifact_key:
            continue
        scope_key = _scope_key_from_artifact(str(artifact_key))
        if scope_key:
            scope_counter[scope_key] += 1
    if not scope_counter:
        return None
    return scope_counter.most_common(1)[0][0]


def compute_features(events: list[dict[str, Any]]) -> EpisodeFeatures:
    total_events = len(events)
    if total_events == 0:
        return EpisodeFeatures(
            total_events=0,
            tool_calls=0,
            tool_results=0,
            user_messages=0,
            agent_reasoning=0,
            corrections=0,
            error_signatures=0,
            git_commits=0,
            unique_artifacts=0,
            repeated_artifact_ratio=0.0,
            correction_ratio=0.0,
            error_ratio=0.0,
            reasoning_ratio=0.0,
            git_ratio=0.0,
            artifact_diversity=0.0,
            dominant_scope_key=None,
            dominant_event_type=None,
            dominant_action=None,
        )

    event_type_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()
    artifacts: list[str] = []

    for event in events:
        event_type = str(event.get("event_type", "unknown"))
        action = str(event.get("action", "unknown"))
        event_type_counter[event_type] += 1
        action_counter[action] += 1
        artifact_key = event.get("artifact_key")
        if artifact_key:
            artifacts.append(str(artifact_key))

    unique_artifacts = len(set(artifacts))
    repeated_artifact_ratio = 0.0
    if artifacts:
        repeated_artifact_ratio = 1.0 - (unique_artifacts / len(artifacts))

    correction_count = event_type_counter.get("correction", 0)
    error_count = event_type_counter.get("error_signature", 0)
    reasoning_count = event_type_counter.get("agent_reasoning", 0)
    git_count = event_type_counter.get("git_commit", 0)

    return EpisodeFeatures(
        total_events=total_events,
        tool_calls=event_type_counter.get("tool_call", 0),
        tool_results=event_type_counter.get("tool_result", 0),
        user_messages=event_type_counter.get("user_message", 0),
        agent_reasoning=reasoning_count,
        corrections=correction_count,
        error_signatures=error_count,
        git_commits=git_count,
        unique_artifacts=unique_artifacts,
        repeated_artifact_ratio=repeated_artifact_ratio,
        correction_ratio=correction_count / total_events,
        error_ratio=error_count / total_events,
        reasoning_ratio=reasoning_count / total_events,
        git_ratio=git_count / total_events,
        artifact_diversity=unique_artifacts / total_events,
        dominant_scope_key=_dominant_scope_key(events),
        dominant_event_type=event_type_counter.most_common(1)[0][0] if event_type_counter else None,
        dominant_action=action_counter.most_common(1)[0][0] if action_counter else None,
    )


def classify_character(features: EpisodeFeatures) -> str:
    if features.total_events <= 0:
        return "exploratory"

    corrective_pressure = features.correction_ratio + features.error_ratio
    interaction_load = features.tool_calls + features.tool_results

    if (
        features.corrections >= 2
        and features.error_signatures >= 1
        and features.unique_artifacts <= 2
        and interaction_load >= 4
    ):
        return "forced"

    if features.corrections >= 2 or features.error_signatures >= 2 or corrective_pressure >= 0.2:
        return "corrective"

    if features.git_commits >= 3 and features.unique_artifacts >= 3:
        return "integrative"

    if features.reasoning_ratio >= 0.2 and features.agent_reasoning >= 2:
        return "deepening"

    if features.unique_artifacts <= 1 and interaction_load >= max(3, features.total_events // 2):
        return "reductive"

    return "exploratory"

