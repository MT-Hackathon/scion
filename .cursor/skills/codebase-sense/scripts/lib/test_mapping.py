# pyright: reportMissingImports=false
from __future__ import annotations

import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import NamedTuple

from .scanner import SourceFile


class TestLink(NamedTuple):
    source_path: str
    test_paths: tuple[str, ...]
    has_tests: bool
    evidence: str


_TEST_DIR_MARKERS = ("/test/", "/tests/", "/__tests__/", "/spec/")
_INLINE_TEST_MARKERS: dict[str, str] = {
    "rust": r"#\[cfg\(test\)\]",
}


def is_test_file(path: str) -> bool:
    normalized = f"/{path.replace('\\', '/').lower()}/"
    if any(marker in normalized for marker in _TEST_DIR_MARKERS):
        return True

    lowered_path = path.replace("\\", "/").lower()
    if lowered_path.endswith(".rs") and "/tests/" in f"/{lowered_path}/":
        return True

    name = PurePosixPath(path).name.lower()
    return (
        ".test." in name
        or ".spec." in name
        or name.startswith("test_")
        or "_test." in name
    )


def map_tests_to_sources(files: list[SourceFile]) -> dict[str, TestLink]:
    source_files = [source_file for source_file in files if not is_test_file(source_file.path)]
    source_paths = [source_file.path for source_file in source_files]
    test_paths = [source_file.path for source_file in files if is_test_file(source_file.path)]
    source_by_filename = _index_sources_by_filename(source_paths)

    mapped_tests: dict[str, list[str]] = {path: [] for path in source_paths}
    mapped_evidence: dict[str, str] = dict.fromkeys(source_paths, "none")

    for test_path in test_paths:
        source_match = _match_source_by_naming(test_path, source_by_filename)
        if source_match is None:
            continue
        mapped_tests[source_match].append(test_path)
        mapped_evidence[source_match] = "naming"

    for source_file in source_files:
        if source_file.language not in _INLINE_TEST_MARKERS:
            continue
        if mapped_tests.get(source_file.path):
            continue
        if _has_inline_tests(source_file.abs_path, source_file.language):
            mapped_evidence[source_file.path] = "inline_cfg_test"

    links: dict[str, TestLink] = {}
    for source_path in sorted(source_paths):
        tests = tuple(sorted(set(mapped_tests.get(source_path, []))))
        evidence = mapped_evidence.get(source_path, "none")
        has_tests = bool(tests) or evidence != "none"
        links[source_path] = TestLink(
            source_path=source_path,
            test_paths=tests,
            has_tests=has_tests,
            evidence=evidence if has_tests else "none",
        )
    return links


def _has_inline_tests(abs_path: Path, language: str) -> bool:
    pattern = _INLINE_TEST_MARKERS.get(language)
    if pattern is None:
        return False
    try:
        content = abs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return re.search(pattern, content) is not None


def _index_sources_by_filename(source_paths: list[str]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for source_path in source_paths:
        key = PurePosixPath(source_path).name.lower()
        if key not in index:
            index[key] = []
        index[key].append(source_path)

    for candidates in index.values():
        candidates.sort()
    return index


def _match_source_by_naming(test_path: str, source_index: dict[str, list[str]]) -> str | None:
    candidate_names = _candidate_source_names(PurePosixPath(test_path).name)
    if not candidate_names:
        return None

    candidate_paths: list[str] = []
    for name in candidate_names:
        candidate_paths.extend(source_index.get(name, []))

    if not candidate_paths:
        return None

    test_parts = PurePosixPath(test_path).parts
    unique_candidates = sorted(set(candidate_paths))
    unique_candidates.sort(
        key=lambda source_path: _source_match_rank(test_parts, PurePosixPath(source_path).parts),
        reverse=True,
    )
    return unique_candidates[0] if unique_candidates else None


def _candidate_source_names(test_filename: str) -> set[str]:
    name = test_filename.lower()
    candidates = {name}

    if ".test." in name:
        candidates.add(name.replace(".test.", ".", 1))
    if ".spec." in name:
        candidates.add(name.replace(".spec.", ".", 1))
    if name.startswith("test_"):
        candidates.add(name.removeprefix("test_"))
    if "_test." in name:
        candidates.add(name.replace("_test.", ".", 1))

    return {candidate for candidate in candidates if candidate}


def _source_match_rank(test_parts: tuple[str, ...], source_parts: tuple[str, ...]) -> tuple[int, int]:
    test_repo = test_parts[0] if test_parts else ""
    source_repo = source_parts[0] if source_parts else ""
    same_repo = 1 if test_repo and test_repo == source_repo else 0
    suffix_match = _common_suffix_len(test_parts[:-1], source_parts[:-1])
    return same_repo, suffix_match


def _common_suffix_len(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    count = 0
    for l_part, r_part in zip(reversed(left), reversed(right), strict=False):
        if l_part != r_part:
            break
        count += 1
    return count
