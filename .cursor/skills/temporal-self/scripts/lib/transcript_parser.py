from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOOL_CALL_RE = re.compile(r"^\[Tool call\]\s+(.+?)\s*$")
TOOL_RESULT_RE = re.compile(r"^\[Tool result\]\s+(.+?)\s*$")
THINKING_RE = re.compile(r"^\[Thinking\]\s*(.*)$")
USER_QUERY_OPEN_RE = re.compile(r"^\s*<user_query>\s*$")
USER_QUERY_CLOSE_RE = re.compile(r"^\s*</user_query>\s*$")

AT_PATH_RE = re.compile(r"@([^\s`]+)")
BACKTICK_RE = re.compile(r"`([^`]+)`")
PATH_TOKEN_RE = re.compile(
    r"([A-Za-z]:[\\/][^\s`'\"<>]+|(?:\.\.?[\\/]|/)?[A-Za-z0-9_.-]+(?:[\\/][A-Za-z0-9_.:@-]+)+|[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,12}(?::\d+(?:-\d+)?)?)"
)
ERROR_TOKEN_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))\b|\b(exit code\s+\d+)\b",
    re.IGNORECASE,
)

COMMAND_PREFIXES = (
    "git ",
    "npm ",
    "npx ",
    "pnpm ",
    "yarn ",
    "uv ",
    "python ",
    "pytest ",
    "gradle ",
    "./gradlew",
    "ng ",
    "ls ",
    "dir ",
    "cd ",
    "echo ",
    "powershell ",
    "pwsh ",
    "bash ",
)

LIKELY_PATH_ROOTS = (
    "src/",
    "test/",
    "tests/",
    "docs/",
    "config/",
    "scripts/",
    "hooks/",
    "cursor/",
    ".cursor/",
)

CORRECTION_PATTERNS = (
    r"\bverify (this|these) issues? exist and fix\b",
    r"\byou are (not|still|missing)\b",
    r"\bnot ready\b",
    r"\bplease have\b",
    r"\bplease (recheck|review|fix|update)\b",
    r"\bi (think|would like|want) .*?(fix|change|update)\b",
    r"\bdid(?:n't| not)\b",
    r"\bsadly\b",
)

REFRAME_PATTERNS = (
    r"\bactually\b(?!.*\b(?:wrong|error|fail|broke|bug|missing)\b)",
    r"\bwhat if\b",
    r"\bthink about it (?:this|another|a different) way\b",
    r"\bthe real question is\b",
    r"\binstead\b(?!.*\b(?:wrong|error|fail|broke|bug|missing)\b)",
    r"\blet me reframe\b",
    r"\blook at (?:it|this) (?:differently|from)\b",
)

TEACHING_PATTERNS = (
    r"\bthe principle (?:is|here)\b",
    r"\bremember that\b",
    r"\bkeep in mind\b",
    r"\bthis is important because\b",
    r"\bby design\b",
    r"\bthere is no cost to\b",
    r"\bthat has no cost\b",
    r"\bworking as (?:intended|designed)\b",
    r"\bthe purpose of\b",
    r"\bthe reason (?:we|I|this)\b",
    r"\bfundamental(?:ly)?\b.*\b(?:principle|rule|pattern|truth)\b",
)

ENDORSEMENT_PATTERNS = (
    r"^(?:exactly|yes,?\s*(?:that'?s?\s*(?:right|it|correct|the\s+right)))\s*[.!]?\s*$",
    r"\bgood instinct\b",
    r"\byou'?re right\b",
    r"\bthat'?s? (?:the right|a good|the correct) (?:call|approach|instinct|move)\b",
    r"\bspot on\b",
    r"\bnailed it\b",
)

CALIBRATION_PATTERNS = (
    r"\bmatch (?:my|his|the) pace\b",
    r"\bwhen I say\b.*\bI mean\b",
    r"\bI (?:want|need|expect) you to\b",
    r"\btake your time\b",
    r"\bdon'?t (?:rush|hurry|get myopic)\b",
    r"\bwe are(?:n'?t)? in (?:a|no) hurry\b",
    r"\bthis (?:is|isn'?t) (?:about|for) you\b",
    r"\byour (?:memories|self[- ]?portrait|momento)\b",
)


def _workspace_roots(workspace_path: Path) -> dict[str, Path]:
    workspace = workspace_path.resolve()
    parent = workspace.parent
    roots: dict[str, Path] = {}
    for child in parent.iterdir():
        if child.is_dir() and (child / ".git").exists():
            roots[child.name] = child.resolve()
    if workspace.name not in roots:
        roots[workspace.name] = workspace
    return roots


def _strip_wrappers(candidate: str) -> str:
    return candidate.strip().strip("`'\"()[]{}<>,")


def _split_line_suffix(candidate: str) -> tuple[str, str]:
    match = re.match(r"^(.*?)(:\d+(?:-\d+)?)$", candidate)
    if not match:
        return candidate, ""
    return match.group(1), match.group(2)


def _normalize_candidate_path(candidate: str, workspace_path: Path) -> str:
    cleaned = _strip_wrappers(candidate).lstrip("@")
    cleaned = cleaned.replace("\\", "/")
    cleaned = re.sub(r"/{2,}", "/", cleaned)
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]

    core, line_suffix = _split_line_suffix(cleaned)
    core = core.strip()
    if not core:
        return ""

    roots = _workspace_roots(workspace_path)
    normalized = core

    absolute_path = Path(core)
    if absolute_path.is_absolute():
        for root_name, root_path in roots.items():
            try:
                relative = absolute_path.resolve().relative_to(root_path)
            except ValueError:
                continue
            rel_posix = relative.as_posix()
            if root_name == workspace_path.name:
                normalized = rel_posix
            else:
                normalized = f"{root_name}/{rel_posix}"
            break
        else:
            normalized = absolute_path.as_posix()
    else:
        normalized = core.replace("\\", "/")
        normalized = normalized.lstrip("./")
        workspace_prefix = f"{workspace_path.name}/"
        if normalized.startswith(workspace_prefix):
            normalized = normalized[len(workspace_prefix) :]

    if normalized.startswith(".cursor/"):
        normalized = normalized[1:]
    if normalized.endswith("/"):
        normalized = normalized[:-1]

    normalized = normalized + line_suffix
    return normalized


def _has_extension(candidate: str) -> bool:
    core, _ = _split_line_suffix(candidate)
    if "/" in core:
        name = core.split("/")[-1]
    else:
        name = core
    return bool(re.search(r"\.[A-Za-z0-9]{1,12}$", name))


def _looks_like_command(candidate: str) -> bool:
    lowered = candidate.lower()
    return any(lowered.startswith(prefix) for prefix in COMMAND_PREFIXES)


def _is_valid_artifact_key(candidate: str) -> bool:
    value = candidate.strip()
    if not value:
        return False
    if any(ch in value for ch in (" ", "\t", "\n", "\r", "|")):
        return False
    if value.startswith(("-", "<", "[")):
        return False
    if _looks_like_command(value):
        return False
    if value.startswith(("http://", "https://")):
        return False
    if "=" in value and "/" not in value and "." not in value:
        return False
    has_separator = "/" in value or "\\" in value
    has_extension = _has_extension(value)
    if not has_separator and not has_extension:
        return False
    if has_extension:
        return True

    normalized = value.replace("\\", "/").lstrip("./")
    core, _ = _split_line_suffix(normalized)
    if re.match(r"^[A-Za-z]:/", core):
        return True
    if any(core.lower().startswith(prefix.lower().lstrip("./")) for prefix in LIKELY_PATH_ROOTS):
        return True
    return False


def _extract_artifact_candidates(text: str) -> list[str]:
    if not text:
        return []
    candidates: list[str] = []
    candidates.extend(AT_PATH_RE.findall(text))
    candidates.extend(BACKTICK_RE.findall(text))
    candidates.extend(match.group(1) for match in PATH_TOKEN_RE.finditer(text))
    return candidates


def _first_artifact_key(text: str, workspace_path: Path) -> str | None:
    for candidate in _extract_artifact_candidates(text):
        normalized = _normalize_candidate_path(candidate, workspace_path)
        if normalized and _is_valid_artifact_key(normalized):
            return normalized
    return None


def _all_artifact_keys(text: str, workspace_path: Path) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for candidate in _extract_artifact_candidates(text):
        normalized = _normalize_candidate_path(candidate, workspace_path)
        if not normalized or not _is_valid_artifact_key(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        keys.append(normalized)
    return keys


def _extract_error_signatures(text: str) -> list[str]:
    signatures: list[str] = []
    seen: set[str] = set()
    for match in ERROR_TOKEN_RE.finditer(text):
        signature = (match.group(1) or match.group(2) or "").strip()
        if not signature:
            continue
        signature = re.sub(r"\s+", " ", signature)
        if signature.lower() in seen:
            continue
        seen.add(signature.lower())
        signatures.append(signature)
    return signatures


def _is_correction(text: str) -> bool:
    content = text.strip()
    if not content:
        return False
    lowered = content.lower()
    for pattern in CORRECTION_PATTERNS:
        if re.search(pattern, lowered):
            return True
    return False


def _is_reframe(text: str) -> bool:
    content = text.strip()
    if not content:
        return False
    lowered = content.lower()
    for pattern in REFRAME_PATTERNS:
        if re.search(pattern, lowered):
            return True
    return False


def _is_teaching(text: str) -> bool:
    content = text.strip()
    if not content:
        return False
    lowered = content.lower()
    for pattern in TEACHING_PATTERNS:
        if re.search(pattern, lowered):
            return True
    return False


def _is_endorsement(text: str) -> bool:
    content = text.strip()
    if not content:
        return False
    if len(content) > 200:
        return False
    lowered = content.lower()
    for pattern in ENDORSEMENT_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            return True
    return False


def _is_calibration(text: str) -> bool:
    content = text.strip()
    if not content:
        return False
    lowered = content.lower()
    for pattern in CALIBRATION_PATTERNS:
        if re.search(pattern, lowered):
            return True
    return False


def _build_event_id(
    session_id: str,
    line_no: int,
    event_type: str,
    per_line_counts: dict[tuple[int, str], int],
) -> str:
    base = f"{session_id}:{line_no}"
    if event_type == "correction":
        return f"{base}:correction"
    if event_type == "reframe":
        return f"{base}:reframe"
    if event_type == "teaching":
        return f"{base}:teaching"
    if event_type == "endorsement":
        return f"{base}:endorsement"
    if event_type == "calibration":
        return f"{base}:calibration"
    if event_type == "error_signature":
        key = (line_no, event_type)
        index = per_line_counts.get(key, 0) + 1
        per_line_counts[key] = index
        return f"{base}:error{index}"
    return base


def _build_event(
    *,
    session_id: str,
    event_time: str,
    knowledge_time: str,
    line_no: int,
    event_type: str,
    action: str,
    artifact_key: str | None,
    status: str,
    payload_json: dict[str, Any] | None,
    source_ref: str,
    per_line_counts: dict[tuple[int, str], int],
) -> dict[str, Any]:
    return {
        "id": _build_event_id(session_id, line_no, event_type, per_line_counts),
        "event_time": event_time,
        "knowledge_time": knowledge_time,
        "strand_id": "main",
        "session_id": session_id,
        "attempt_id": None,
        "event_type": event_type,
        "action": action,
        "artifact_key": artifact_key,
        "status": status,
        "payload_json": payload_json,
        "causal_antecedent_id": None,
        "causal_type": None,
        "revelation": None,
        "episode_character": None,
        "coherence_signal": None,
        "confidence": 1.0,
        "source_ref": source_ref,
    }


def _build_link(source_event_id: str, target_event_id: str, link_type: str) -> dict[str, Any]:
    digest = hashlib.sha256(f"{source_event_id}>{target_event_id}>{link_type}".encode("utf-8")).hexdigest()
    return {
        "id": f"link:{digest[:24]}",
        "source_event_id": source_event_id,
        "target_event_id": target_event_id,
        "link_type": link_type,
        "pre_pivot_focus_json": None,
        "post_pivot_focus_json": None,
        "inferred_revelation": None,
        "extraction_method": "transcript-heuristic",
        "confidence": 0.8,
    }


def parse_jsonl_transcript(
    transcript_path: Path,
    workspace_path: Path,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Parse a Cursor JSONL transcript into temporal-self events."""
    if not transcript_path.exists():
        return [], [], transcript_path.stem

    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    session_id = transcript_path.stem
    file_mtime = transcript_path.stat().st_mtime
    event_time = datetime.fromtimestamp(file_mtime, tz=timezone.utc).isoformat()
    knowledge_time = datetime.now(timezone.utc).isoformat()
    source_name = transcript_path.name

    events: list[dict[str, Any]] = []
    per_line_counts: dict[tuple[int, str], int] = {}
    turn_index = 0

    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        role = entry.get("role", "")
        message = entry.get("message", {})
        content_blocks = message.get("content", [])
        turn_text_parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                turn_text_parts.append(block.get("text", ""))
        turn_text = "\n".join(turn_text_parts).strip()
        if not turn_text:
            turn_index += 1
            continue

        line_no = turn_index + 1

        if role == "user":
            # Extract text from <user_query> tags if present
            query_match = re.search(
                r"<user_query>\s*(.*?)\s*</user_query>",
                turn_text,
                re.DOTALL,
            )
            user_text = query_match.group(1).strip() if query_match else turn_text
            artifact_key = _first_artifact_key(user_text, workspace_path)

            user_event = _build_event(
                session_id=session_id,
                event_time=event_time,
                knowledge_time=knowledge_time,
                line_no=line_no,
                event_type="user_message",
                action="user_input",
                artifact_key=artifact_key,
                status="unknown",
                payload_json={"text": user_text},
                source_ref=f"{source_name}:{line_no}",
                per_line_counts=per_line_counts,
            )
            events.append(user_event)

            if _is_correction(user_text):
                events.append(
                    _build_event(
                        session_id=session_id,
                        event_time=event_time,
                        knowledge_time=knowledge_time,
                        line_no=line_no,
                        event_type="correction",
                        action="user_feedback",
                        artifact_key=artifact_key,
                        status="success",
                        payload_json={"text": user_text},
                        source_ref=f"{source_name}:{line_no}",
                        per_line_counts=per_line_counts,
                    )
                )

            if _is_reframe(user_text):
                events.append(
                    _build_event(
                        session_id=session_id,
                        event_time=event_time,
                        knowledge_time=knowledge_time,
                        line_no=line_no,
                        event_type="reframe",
                        action="user_reframe",
                        artifact_key=artifact_key,
                        status="success",
                        payload_json={"text": user_text},
                        source_ref=f"{source_name}:{line_no}",
                        per_line_counts=per_line_counts,
                    )
                )

            if _is_teaching(user_text):
                events.append(
                    _build_event(
                        session_id=session_id,
                        event_time=event_time,
                        knowledge_time=knowledge_time,
                        line_no=line_no,
                        event_type="teaching",
                        action="user_teaching",
                        artifact_key=artifact_key,
                        status="success",
                        payload_json={"text": user_text},
                        source_ref=f"{source_name}:{line_no}",
                        per_line_counts=per_line_counts,
                    )
                )

            if _is_endorsement(user_text):
                events.append(
                    _build_event(
                        session_id=session_id,
                        event_time=event_time,
                        knowledge_time=knowledge_time,
                        line_no=line_no,
                        event_type="endorsement",
                        action="user_endorsement",
                        artifact_key=artifact_key,
                        status="success",
                        payload_json={"text": user_text},
                        source_ref=f"{source_name}:{line_no}",
                        per_line_counts=per_line_counts,
                    )
                )

            if _is_calibration(user_text):
                events.append(
                    _build_event(
                        session_id=session_id,
                        event_time=event_time,
                        knowledge_time=knowledge_time,
                        line_no=line_no,
                        event_type="calibration",
                        action="user_calibration",
                        artifact_key=artifact_key,
                        status="success",
                        payload_json={"text": user_text},
                        source_ref=f"{source_name}:{line_no}",
                        per_line_counts=per_line_counts,
                    )
                )

        elif role == "assistant":
            artifact_key = _first_artifact_key(turn_text, workspace_path)
            events.append(
                _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=line_no,
                    event_type="agent_reasoning",
                    action="thinking",
                    artifact_key=artifact_key,
                    status="unknown",
                    payload_json={"text": turn_text[:500]},
                    source_ref=f"{source_name}:{line_no}",
                    per_line_counts=per_line_counts,
                )
            )

            for signature in _extract_error_signatures(turn_text):
                events.append(
                    _build_event(
                        session_id=session_id,
                        event_time=event_time,
                        knowledge_time=knowledge_time,
                        line_no=line_no,
                        event_type="error_signature",
                        action=signature,
                        artifact_key=artifact_key,
                        status="failure",
                        payload_json={"signature": signature},
                        source_ref=f"{source_name}:{line_no}",
                        per_line_counts=per_line_counts,
                    )
                )

        turn_index += 1

    if verbose:
        print(
            f"[transcript_parser] {transcript_path.name} (jsonl): "
            f"{len(events)} events"
        )

    return events, [], session_id


def parse_transcript(
    transcript_path: Path,
    workspace_path: Path,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    if transcript_path.suffix.lower() == ".jsonl":
        return parse_jsonl_transcript(transcript_path, workspace_path, verbose=verbose)
    if not transcript_path.exists():
        return [], [], transcript_path.stem

    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    session_id = transcript_path.stem
    event_time = datetime.fromtimestamp(transcript_path.stat().st_mtime, tz=timezone.utc).isoformat()
    knowledge_time = datetime.now(timezone.utc).isoformat()
    source_name = transcript_path.name

    events: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    per_line_counts: dict[tuple[int, str], int] = {}
    pending_tool_calls: dict[str, list[str]] = {}

    i = 0
    while i < len(lines):
        line_no = i + 1
        line = lines[i]
        stripped = line.strip()

        if USER_QUERY_OPEN_RE.match(stripped):
            query_lines: list[str] = []
            start_line_no = line_no
            i += 1
            while i < len(lines) and not USER_QUERY_CLOSE_RE.match(lines[i].strip()):
                query_lines.append(lines[i])
                i += 1
            user_text = "\n".join(query_lines).strip()
            artifact_key = _first_artifact_key(user_text, workspace_path)
            user_event = _build_event(
                session_id=session_id,
                event_time=event_time,
                knowledge_time=knowledge_time,
                line_no=start_line_no,
                event_type="user_message",
                action="user_input",
                artifact_key=artifact_key,
                status="unknown",
                payload_json={"text": user_text},
                source_ref=f"{source_name}:{start_line_no}",
                per_line_counts=per_line_counts,
            )
            events.append(user_event)

            if _is_correction(user_text):
                correction_event = _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=start_line_no,
                    event_type="correction",
                    action="user_feedback",
                    artifact_key=artifact_key,
                    status="success",
                    payload_json={"text": user_text},
                    source_ref=f"{source_name}:{start_line_no}",
                    per_line_counts=per_line_counts,
                )
                events.append(correction_event)

            if _is_reframe(user_text):
                reframe_event = _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=start_line_no,
                    event_type="reframe",
                    action="user_reframe",
                    artifact_key=artifact_key,
                    status="success",
                    payload_json={"text": user_text},
                    source_ref=f"{source_name}:{start_line_no}",
                    per_line_counts=per_line_counts,
                )
                events.append(reframe_event)

            if _is_teaching(user_text):
                teaching_event = _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=start_line_no,
                    event_type="teaching",
                    action="user_teaching",
                    artifact_key=artifact_key,
                    status="success",
                    payload_json={"text": user_text},
                    source_ref=f"{source_name}:{start_line_no}",
                    per_line_counts=per_line_counts,
                )
                events.append(teaching_event)

            if _is_endorsement(user_text):
                endorsement_event = _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=start_line_no,
                    event_type="endorsement",
                    action="user_endorsement",
                    artifact_key=artifact_key,
                    status="success",
                    payload_json={"text": user_text},
                    source_ref=f"{source_name}:{start_line_no}",
                    per_line_counts=per_line_counts,
                )
                events.append(endorsement_event)

            if _is_calibration(user_text):
                calibration_event = _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=start_line_no,
                    event_type="calibration",
                    action="user_calibration",
                    artifact_key=artifact_key,
                    status="success",
                    payload_json={"text": user_text},
                    source_ref=f"{source_name}:{start_line_no}",
                    per_line_counts=per_line_counts,
                )
                events.append(calibration_event)
            i += 1
            continue

        thinking_match = THINKING_RE.match(stripped)
        if thinking_match:
            thought_lines = [thinking_match.group(1)] if thinking_match.group(1) else []
            start_line_no = line_no
            i += 1
            while i < len(lines):
                probe = lines[i].strip()
                if (
                    probe == "assistant:"
                    or probe == "user:"
                    or USER_QUERY_OPEN_RE.match(probe)
                    or TOOL_CALL_RE.match(probe)
                    or TOOL_RESULT_RE.match(probe)
                ):
                    break
                thought_lines.append(lines[i])
                i += 1
            thought_text = "\n".join(thought_lines).strip()
            artifact_key = _first_artifact_key(thought_text, workspace_path)
            event = _build_event(
                session_id=session_id,
                event_time=event_time,
                knowledge_time=knowledge_time,
                line_no=start_line_no,
                event_type="agent_reasoning",
                action="thinking",
                artifact_key=artifact_key,
                status="unknown",
                payload_json={"text": thought_text},
                source_ref=f"{source_name}:{start_line_no}",
                per_line_counts=per_line_counts,
            )
            events.append(event)

            error_signatures = _extract_error_signatures(thought_text)
            for signature in error_signatures:
                error_event = _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=start_line_no,
                    event_type="error_signature",
                    action=signature,
                    artifact_key=artifact_key,
                    status="failure",
                    payload_json={"signature": signature},
                    source_ref=f"{source_name}:{start_line_no}",
                    per_line_counts=per_line_counts,
                )
                events.append(error_event)
            continue

        tool_call_match = TOOL_CALL_RE.match(stripped)
        if tool_call_match:
            tool_name = tool_call_match.group(1).strip()
            start_line_no = line_no
            i += 1
            param_lines: list[str] = []
            while i < len(lines):
                probe = lines[i]
                probe_stripped = probe.strip()
                if (
                    probe_stripped == "assistant:"
                    or probe_stripped == "user:"
                    or USER_QUERY_OPEN_RE.match(probe_stripped)
                    or TOOL_CALL_RE.match(probe_stripped)
                    or TOOL_RESULT_RE.match(probe_stripped)
                ):
                    break
                if probe.startswith("  ") or not probe_stripped:
                    param_lines.append(probe)
                    i += 1
                    continue
                break

            params: dict[str, str] = {}
            current_key: str | None = None
            for raw in param_lines:
                chunk = raw.strip()
                if not chunk:
                    continue
                if ":" in chunk:
                    key, value = chunk.split(":", 1)
                    current_key = key.strip()
                    params[current_key] = value.strip()
                    continue
                if current_key:
                    params[current_key] = f"{params[current_key]}\n{chunk}".strip()

            path_candidates: list[str] = []
            for value in params.values():
                path_candidates.extend(_all_artifact_keys(value, workspace_path))
            artifact_key = path_candidates[0] if path_candidates else None

            event = _build_event(
                session_id=session_id,
                event_time=event_time,
                knowledge_time=knowledge_time,
                line_no=start_line_no,
                event_type="tool_call",
                action=tool_name,
                artifact_key=artifact_key,
                status="unknown",
                payload_json={"tool": tool_name, "params": params, "paths": path_candidates},
                source_ref=f"{source_name}:{start_line_no}",
                per_line_counts=per_line_counts,
            )
            events.append(event)
            pending_tool_calls.setdefault(tool_name, []).append(event["id"])
            continue

        tool_result_match = TOOL_RESULT_RE.match(stripped)
        if tool_result_match:
            tool_name = tool_result_match.group(1).strip()
            start_line_no = line_no
            i += 1
            result_lines: list[str] = []
            while i < len(lines):
                probe = lines[i].strip()
                if (
                    probe == "assistant:"
                    or probe == "user:"
                    or USER_QUERY_OPEN_RE.match(probe)
                    or TOOL_CALL_RE.match(probe)
                    or TOOL_RESULT_RE.match(probe)
                ):
                    break
                result_lines.append(lines[i])
                i += 1

            result_text = "\n".join(result_lines).strip()
            artifact_key = _first_artifact_key(result_text, workspace_path)
            event = _build_event(
                session_id=session_id,
                event_time=event_time,
                knowledge_time=knowledge_time,
                line_no=start_line_no,
                event_type="tool_result",
                action=tool_name,
                artifact_key=artifact_key,
                status="unknown",
                payload_json={"tool": tool_name},
                source_ref=f"{source_name}:{start_line_no}",
                per_line_counts=per_line_counts,
            )
            events.append(event)

            pending_ids = pending_tool_calls.get(tool_name, [])
            if pending_ids:
                source_event_id = pending_ids.pop(0)
                links.append(_build_link(source_event_id, event["id"], "tool_response"))

            error_signatures = _extract_error_signatures(result_text)
            for signature in error_signatures:
                error_event = _build_event(
                    session_id=session_id,
                    event_time=event_time,
                    knowledge_time=knowledge_time,
                    line_no=start_line_no,
                    event_type="error_signature",
                    action=signature,
                    artifact_key=artifact_key,
                    status="failure",
                    payload_json={"signature": signature},
                    source_ref=f"{source_name}:{start_line_no}",
                    per_line_counts=per_line_counts,
                )
                events.append(error_event)
            continue

        i += 1

    if verbose:
        print(
            f"[transcript_parser] {transcript_path.name}: "
            f"{len(events)} events, {len(links)} links"
        )

    return events, links, session_id


def parse_transcripts(
    transcript_paths: list[Path],
    workspace_path: Path,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    all_events: list[dict[str, Any]] = []
    all_links: list[dict[str, Any]] = []
    sessions: set[str] = set()

    for transcript_path in transcript_paths:
        events, links, session_id = parse_transcript(transcript_path, workspace_path, verbose=verbose)
        if events:
            all_events.extend(events)
            all_links.extend(links)
            sessions.add(session_id)

    # Deterministic ordering for stable inserts.
    all_events.sort(key=lambda event: (event["event_time"], event["id"]))
    all_links.sort(key=lambda link: link["id"])
    return all_events, all_links, sessions


def summarize_transcript_event_types(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("event_type", "unknown"))
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def dump_events_json(events: list[dict[str, Any]]) -> str:
    return json.dumps(events, ensure_ascii=True, indent=2)

