#!/usr/bin/env -S uv run --script --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

_HOOK_PATH = Path(__file__).resolve().parent.parent / "executor-quality-gate.py"
_SPEC = importlib.util.spec_from_file_location("executor_quality_gate", _HOOK_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_mod = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _mod
_SPEC.loader.exec_module(_mod)


def _violation_messages(report):
    return [violation.message for violation in report.violations]


class TestLoadCoverageThresholds:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        result = _mod._load_coverage_thresholds(tmp_path)
        assert result == {"lines": 90, "functions": 90, "branches": 90, "statements": 90}

    def test_reads_from_config_file(self, tmp_path):
        config_dir = tmp_path / "app"
        config_dir.mkdir()
        config_file = config_dir / "coverage-thresholds.json"
        config_file.write_text(json.dumps({"lines": 85, "functions": 85, "branches": 85, "statements": 85}))
        result = _mod._load_coverage_thresholds(tmp_path)
        assert result == {"lines": 85, "functions": 85, "branches": 85, "statements": 85}

    def test_falls_back_on_invalid_json(self, tmp_path):
        config_dir = tmp_path / "app"
        config_dir.mkdir()
        config_file = config_dir / "coverage-thresholds.json"
        config_file.write_text("not valid json")
        result = _mod._load_coverage_thresholds(tmp_path)
        assert result == {"lines": 90, "functions": 90, "branches": 90, "statements": 90}

    def test_falls_back_on_non_dict_json(self, tmp_path):
        config_dir = tmp_path / "app"
        config_dir.mkdir()
        config_file = config_dir / "coverage-thresholds.json"
        config_file.write_text("[1, 2, 3]")
        result = _mod._load_coverage_thresholds(tmp_path)
        assert result == {"lines": 90, "functions": 90, "branches": 90, "statements": 90}

    def test_uses_defaults_for_missing_keys(self, tmp_path):
        config_dir = tmp_path / "app"
        config_dir.mkdir()
        config_file = config_dir / "coverage-thresholds.json"
        config_file.write_text(json.dumps({"lines": 80}))
        result = _mod._load_coverage_thresholds(tmp_path)
        assert result == {"lines": 80, "functions": 90, "branches": 90, "statements": 90}


class TestIsCompletedEvent:
    def test_returns_true_for_completed_status(self):
        event = {"subagent_type": "general-purpose", "status": "completed"}
        assert _mod._is_completed_event(event) is True

    def test_returns_true_regardless_of_subagent_type(self):
        event = {"subagent_type": "the-executor", "status": "completed"}
        assert _mod._is_completed_event(event) is True

    def test_returns_false_for_error_status(self):
        event = {"subagent_type": "general-purpose", "status": "error"}
        assert _mod._is_completed_event(event) is False

    def test_returns_false_when_status_missing(self):
        event = {"subagent_type": "general-purpose"}
        assert _mod._is_completed_event(event) is False

    def test_returns_false_for_empty_dict(self):
        assert _mod._is_completed_event({}) is False


class TestDiscoverChangedFiles:
    def test_uses_result_text_when_present(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        event = {"result": "Changed `src/module.py` successfully"}
        paths = _mod._discover_changed_files(event, tmp_path)
        assert len(paths) == 1
        assert paths[0].name == "module.py"

    def test_falls_back_to_git_diff_when_no_result(self, monkeypatch, tmp_path):
        event = {"status": "completed"}

        def fake_run(cmd, **kwargs):
            if "diff" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0,
                    stdout="app/backend/src/graft/models.py\n", stderr=""
                )
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        paths = _mod._discover_changed_files(event, tmp_path)
        assert len(paths) == 1
        assert paths[0].name == "models.py"

    def test_filters_to_supported_extensions(self, monkeypatch, tmp_path):
        event = {"status": "completed"}

        def fake_run(cmd, **kwargs):
            if "diff" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0,
                    stdout="readme.md\nmodule.py\nconfig.json\n", stderr=""
                )
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        paths = _mod._discover_changed_files(event, tmp_path)
        assert len(paths) == 1
        assert paths[0].name == "module.py"

    def test_returns_empty_when_no_changes(self, monkeypatch, tmp_path):
        event = {"status": "completed"}

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        paths = _mod._discover_changed_files(event, tmp_path)
        assert paths == []

    def test_handles_git_not_found(self, monkeypatch, tmp_path):
        event = {"status": "completed"}

        def fake_run(cmd, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", fake_run)
        paths = _mod._discover_changed_files(event, tmp_path)
        assert paths == []

    def test_uses_transcript_when_no_result(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": "Files: `src/changed.py`"}]}}),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")
        event = {"status": "completed", "agent_transcript_path": str(transcript)}
        paths = _mod._discover_changed_files(event, tmp_path)
        assert len(paths) == 1
        assert paths[0].name == "changed.py"

    def test_prefers_result_over_transcript(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": "Files: `src/from_transcript.py`"}]}}),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")
        event = {"result": "Changed `src/from_result.py`", "agent_transcript_path": str(transcript)}
        paths = _mod._discover_changed_files(event, tmp_path)
        assert len(paths) == 1
        assert paths[0].name == "from_result.py"


class TestExtractPathsFromTranscript:
    def test_extracts_paths_from_last_assistant_message(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "Do something"}]}}),
            json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": "Working on it"}]}}),
            json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": "Files touched: `src/module.py`"}]}}),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")
        paths = _mod._extract_paths_from_transcript(str(transcript))
        assert len(paths) == 1
        assert paths[0].name == "module.py"

    def test_uses_last_assistant_message_not_first(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": "Changed `old/file.py`"}]}}),
            json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": "Final: `src/final.py`"}]}}),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")
        paths = _mod._extract_paths_from_transcript(str(transcript))
        assert len(paths) == 1
        assert paths[0].name == "final.py"

    def test_returns_empty_for_none_path(self):
        assert _mod._extract_paths_from_transcript(None) == []

    def test_returns_empty_for_nonexistent_file(self):
        assert _mod._extract_paths_from_transcript("/nonexistent/path.jsonl") == []

    def test_returns_empty_when_no_paths_in_transcript(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": "All done, no files listed"}]}}),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")
        paths = _mod._extract_paths_from_transcript(str(transcript))
        assert paths == []

    def test_handles_malformed_jsonl(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("not json\n{bad\n", encoding="utf-8")
        paths = _mod._extract_paths_from_transcript(str(transcript))
        assert paths == []


class TestExtractPaths:
    def test_extracts_backtick_wrapped_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        text = "Touched `app/backend/src/graft/models.py` during refactor."
        paths = _mod._extract_paths(text)
        assert len(paths) == 1
        assert paths[0].as_posix().endswith("app/backend/src/graft/models.py")

    def test_extracts_bullet_list_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        text = "- app/backend/src/graft/models.py - added new model"
        paths = _mod._extract_paths(text)
        assert len(paths) == 1
        assert paths[0].as_posix().endswith("app/backend/src/graft/models.py")

    def test_extracts_bare_path_with_regex_fallback(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        text = "Updated app/backend/src/graft/models.py and moved on."
        paths = _mod._extract_paths(text)
        assert len(paths) == 1
        assert paths[0].as_posix().endswith("app/backend/src/graft/models.py")

    def test_filters_unsupported_extensions(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        text = "Edited `notes.md` and `config.yaml` only."
        paths = _mod._extract_paths(text)
        assert paths == []

    def test_returns_empty_list_for_empty_string(self):
        assert _mod._extract_paths("") == []

    def test_resolves_relative_paths_against_workspace(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_mod, "WORKSPACE_PATH", tmp_path)
        text = "Changed src/pkg/module.py"
        paths = _mod._extract_paths(text)
        expected = (tmp_path / "src/pkg/module.py").resolve()
        assert expected in paths

    def test_handles_windows_style_absolute_path(self):
        text = r"Touched C:\foo\bar.py for hotfix."
        paths = _mod._extract_paths(text)
        assert any(path.name == "bar.py" for path in paths)


class TestIsTestFile:
    def test_detects_test_prefix_python(self):
        assert _mod._is_test_file(Path("test_something.py")) is True

    def test_detects_test_suffix_python(self):
        assert _mod._is_test_file(Path("something_test.py")) is True

    def test_detects_dot_test_ts(self):
        assert _mod._is_test_file(Path("something.test.ts")) is True

    def test_detects_spec_ts(self):
        assert _mod._is_test_file(Path("something_spec.ts")) is True

    def test_regular_python_file_is_not_test(self):
        assert _mod._is_test_file(Path("something.py")) is False

    def test_regular_ts_file_is_not_test(self):
        assert _mod._is_test_file(Path("something.ts")) is False

    def test_test_prefix_ts_is_not_marked_as_test(self):
        assert _mod._is_test_file(Path("test_utils.ts")) is False


class TestAnalyzePython:
    def test_clean_short_function_has_no_violations(self):
        source = textwrap.dedent(
            """
            def add(a, b):
                return a + b
            """
        )
        report = _mod._analyze_python(Path("clean.py"), source)
        assert report.violations == []

    def test_function_over_60_lines_reports_length_violation(self):
        body = "\n".join("    x += 1" for _ in range(61))
        source = f"def long_fn():\n    x = 0\n{body}\n    return x\n"
        report = _mod._analyze_python(Path("long.py"), source)
        messages = _violation_messages(report)
        assert any("is 64 lines" in message and "limit: 60" in message for message in messages)

    def test_deep_nesting_reports_violation(self):
        source = textwrap.dedent(
            """
            def nested(v):
                if v > 0:
                    for i in range(3):
                        while i < 2:
                            if i == 1:
                                return i
                return 0
            """
        )
        report = _mod._analyze_python(Path("nested.py"), source)
        messages = _violation_messages(report)
        assert any("Nesting depth of 4" in message for message in messages)

    def test_eval_call_reports_violation(self):
        source = textwrap.dedent(
            """
            def run(code):
                return eval(code)
            """
        )
        report = _mod._analyze_python(Path("eval_use.py"), source)
        messages = _violation_messages(report)
        assert any("`eval()` call" in message for message in messages)

    def test_exec_call_reports_violation(self):
        source = textwrap.dedent(
            """
            def run(code):
                exec(code)
            """
        )
        report = _mod._analyze_python(Path("exec_use.py"), source)
        messages = _violation_messages(report)
        assert any("`exec()` call" in message for message in messages)

    def test_more_than_three_type_ignores_reports_violation(self):
        source = textwrap.dedent(
            """
            x = 1  # type: ignore
            y = 2  # type: ignore
            z = 3  # type: ignore
            q = 4  # type: ignore
            """
        )
        report = _mod._analyze_python(Path("types.py"), source)
        messages = _violation_messages(report)
        assert any("`# type: ignore` count is 4" in message for message in messages)

    def test_magic_number_reports_violation(self):
        source = textwrap.dedent(
            """
            def calc():
                return 42
            """
        )
        report = _mod._analyze_python(Path("magic.py"), source)
        messages = _violation_messages(report)
        assert any("Potential magic number `42`" in message for message in messages)

    def test_magic_number_in_uppercase_const_is_exempt(self):
        source = "CONST = 42\n"
        report = _mod._analyze_python(Path("consts.py"), source)
        assert report.violations == []

    def test_minus_one_zero_one_are_exempt(self):
        source = textwrap.dedent(
            """
            def baseline():
                a = -1
                b = 0
                c = 1
                return a + b + c
            """
        )
        report = _mod._analyze_python(Path("bounds.py"), source)
        messages = _violation_messages(report)
        assert not any("Potential magic number" in message for message in messages)

    def test_syntax_error_returns_empty_violations(self):
        source = "def broken(\n    return 1\n"
        report = _mod._analyze_python(Path("broken.py"), source)
        assert report.violations == []

    def test_else_count_is_populated_in_info(self):
        source = textwrap.dedent(
            """
            def branch(v):
                if v == 0:
                    return 0
                elif v == 1:
                    return 1
                else:
                    return 2
            """
        )
        report = _mod._analyze_python(Path("branch.py"), source)
        assert report.info["else_count"] == 2


class TestAnalyzeJsLike:
    def test_var_declaration_reports_violation(self):
        source = "var x = 1;"
        report = _mod._analyze_js_like(Path("a.ts"), source)
        messages = _violation_messages(report)
        assert any("`var` declaration" in message for message in messages)

    def test_const_declaration_has_no_var_violation(self):
        source = "const x = 1;"
        report = _mod._analyze_js_like(Path("a.ts"), source)
        messages = _violation_messages(report)
        assert not any("`var` declaration" in message for message in messages)

    def test_eval_usage_reports_dynamic_evaluation_violation(self):
        source = "const out = eval(code);"
        report = _mod._analyze_js_like(Path("a.ts"), source)
        messages = _violation_messages(report)
        assert any("Dynamic evaluation usage" in message for message in messages)

    def test_function_block_over_60_lines_reports_violation(self):
        body = "\n".join("  x += 1;" for _ in range(61))
        source = f"function longFn() {{\n  let x = 0;\n{body}\n  return x;\n}}"
        report = _mod._analyze_js_like(Path("long.ts"), source)
        messages = _violation_messages(report)
        assert any("Function block near line 1" in message and "limit: 60" in message for message in messages)

    def test_deep_brace_nesting_reports_violation(self):
        source = textwrap.dedent(
            """
            function demo() {
              if (a) {
                while (b) {
                  for (;;) {
                    if (c) {
                      return 1;
                    }
                  }
                }
              }
            }
            """
        )
        report = _mod._analyze_js_like(Path("nest.ts"), source)
        messages = _violation_messages(report)
        assert any("Nesting depth of 5" in message for message in messages)


class TestExtractSvelteScript:
    def test_extracts_single_script_block(self):
        source = textwrap.dedent(
            """
            <script>
            const x = 1;
            </script>
            <h1>Hello</h1>
            """
        )
        extracted = _mod._extract_svelte_script(source)
        assert "const x = 1;" in extracted

    def test_handles_script_with_lang_attribute(self):
        source = textwrap.dedent(
            """
            <script lang="ts">
            let count: number = 0;
            </script>
            """
        )
        extracted = _mod._extract_svelte_script(source)
        assert "let count: number = 0;" in extracted

    def test_returns_empty_string_when_no_script_tag_exists(self):
        extracted = _mod._extract_svelte_script("<div>No script here</div>")
        assert extracted == ""

    def test_handles_multiple_script_blocks(self):
        source = textwrap.dedent(
            """
            <script context="module">
            export const prerender = true;
            </script>
            <script lang="ts">
            let ready = false;
            </script>
            <main />
            """
        )
        extracted = _mod._extract_svelte_script(source)
        assert "export const prerender = true;" in extracted
        assert "let ready = false;" in extracted


class TestAnalyzeJava:
    def test_short_method_has_no_violations(self):
        source = textwrap.dedent(
            """
            public class Demo {
                public int add(int a, int b) {
                    return a + b;
                }
            }
            """
        )
        report = _mod._analyze_java(Path("Demo.java"), source)
        assert report.violations == []

    def test_method_over_60_lines_reports_length_violation(self):
        body = "\n".join("            x++;" for _ in range(61))
        source = (
            "public class Demo {\n"
            "    public int longMethod() {\n"
            "        int x = 0;\n"
            f"{body}\n"
            "        return x;\n"
            "    }\n"
            "}\n"
        )
        report = _mod._analyze_java(Path("Demo.java"), source)
        messages = _violation_messages(report)
        assert any("Method near line 2" in message and "limit: 60" in message for message in messages)

    def test_two_short_methods_do_not_trigger_nesting_violation(self):
        source = textwrap.dedent(
            """
            public class Demo {
                public int one(int value) {
                    if (value > 0) {
                        return value;
                    }
                    return 0;
                }

                public int two(int value) {
                    if (value > 1) {
                        return value - 1;
                    }
                    return 1;
                }
            }
            """
        )
        report = _mod._analyze_java(Path("Demo.java"), source)
        messages = _violation_messages(report)
        assert not any("Nesting depth" in message for message in messages)

    def test_single_method_with_deep_nesting_triggers_violation(self):
        source = textwrap.dedent(
            """
            public class Demo {
                public int nested(int value) {
                    if (value > 0) {
                        for (int i = 0; i < value; i++) {
                            while (i < 5) {
                                if (i % 2 == 0) {
                                    return i;
                                }
                            }
                        }
                    }
                    return 0;
                }
            }
            """
        )
        report = _mod._analyze_java(Path("Demo.java"), source)
        messages = _violation_messages(report)
        assert any("Nesting depth of 4" in message for message in messages)


class TestRunRuff:
    def test_returns_empty_list_when_ruff_not_found(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise FileNotFoundError

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_ruff([Path("test.py")])
        assert violations == []

    def test_returns_empty_list_for_empty_file_list(self):
        assert _mod._run_ruff([]) == []

    def test_parses_ruff_json_output(self, monkeypatch):
        ruff_output = json.dumps(
            [
                {
                    "code": "E501",
                    "message": "Line too long",
                    "location": {"row": 10},
                    "filename": "test.py",
                }
            ]
        )

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=1, stdout=ruff_output, stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_ruff([Path("test.py")])
        assert len(violations) == 1
        assert "E501" in violations[0].message
        assert violations[0].line == 10

    def test_handles_timeout_gracefully(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="ruff", timeout=1)

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_ruff([Path("test.py")])
        assert violations == []


class TestRunEslint:
    def test_returns_empty_list_when_frontend_dir_missing(self, tmp_path):
        violations = _mod._run_eslint([Path("app/frontend/src/file.ts")], tmp_path)
        assert violations == []

    def test_returns_empty_list_for_empty_file_list(self, tmp_path):
        assert _mod._run_eslint([], tmp_path) == []

    def test_parses_eslint_json_output(self, monkeypatch, tmp_path):
        frontend_dir = tmp_path / "app" / "frontend"
        frontend_dir.mkdir(parents=True)
        eslint_output = json.dumps(
            [
                {
                    "filePath": str(frontend_dir / "src" / "App.svelte"),
                    "messages": [
                        {
                            "severity": 2,
                            "ruleId": "no-eval",
                            "message": "eval can be harmful",
                            "line": 12,
                        }
                    ],
                }
            ]
        )

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=1, stdout=eslint_output, stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_eslint([Path("src/App.svelte")], tmp_path)
        assert len(violations) == 1
        assert "no-eval" in violations[0].message
        assert violations[0].line == 12

    def test_only_includes_severity_two_errors(self, monkeypatch, tmp_path):
        frontend_dir = tmp_path / "app" / "frontend"
        frontend_dir.mkdir(parents=True)
        eslint_output = json.dumps(
            [
                {
                    "filePath": str(frontend_dir / "src" / "file.ts"),
                    "messages": [
                        {
                            "severity": 1,
                            "ruleId": "no-console",
                            "message": "Unexpected console statement",
                            "line": 2,
                        },
                        {
                            "severity": 2,
                            "ruleId": "no-undef",
                            "message": "x is not defined",
                            "line": 3,
                        },
                    ],
                }
            ]
        )

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=1, stdout=eslint_output, stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_eslint([Path("src/file.ts")], tmp_path)
        assert len(violations) == 1
        assert "no-undef" in violations[0].message


class TestDetectStacks:
    def test_backend_file_detected(self, tmp_path):
        workspace = tmp_path
        (workspace / "app" / "backend" / "src").mkdir(parents=True)
        (workspace / "app" / "backend" / "pyproject.toml").write_text("[project]", encoding="utf-8")
        path = (workspace / "app" / "backend" / "src" / "module.py").resolve()
        result = _mod._detect_stacks([path], workspace)
        assert result["backend"] is True
        assert result["frontend"] is False

    def test_frontend_file_detected(self, tmp_path):
        workspace = tmp_path
        (workspace / "app" / "frontend" / "src").mkdir(parents=True)
        (workspace / "app" / "frontend" / "package.json").write_text("{}", encoding="utf-8")
        path = (workspace / "app" / "frontend" / "src" / "lib" / "component.ts").resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        result = _mod._detect_stacks([path], workspace)
        assert result["frontend"] is True
        assert result["backend"] is False

    def test_both_stacks_detected(self, tmp_path):
        workspace = tmp_path
        (workspace / "app" / "backend" / "src").mkdir(parents=True)
        (workspace / "app" / "frontend" / "src").mkdir(parents=True)
        (workspace / "app" / "backend" / "pyproject.toml").write_text("[project]", encoding="utf-8")
        (workspace / "app" / "frontend" / "package.json").write_text("{}", encoding="utf-8")
        py = (workspace / "app" / "backend" / "src" / "m.py").resolve()
        ts = (workspace / "app" / "frontend" / "src" / "m.ts").resolve()
        result = _mod._detect_stacks([py, ts], workspace)
        assert result["backend"] is True
        assert result["frontend"] is True

    def test_no_stacks_for_unrelated_paths(self, tmp_path):
        result = _mod._detect_stacks([tmp_path / "random.py"], tmp_path)
        assert result["backend"] is False
        assert result["frontend"] is False


class TestRunBackendCoverage:
    def test_returns_empty_when_backend_dir_missing(self, tmp_path):
        violations = _mod._run_backend_coverage(tmp_path)
        assert violations == []

    def test_returns_violation_when_below_threshold(self, tmp_path, monkeypatch):
        backend_dir = tmp_path / "app" / "backend"
        backend_dir.mkdir(parents=True)
        (tmp_path / "app" / "coverage-thresholds.json").write_text(
            json.dumps({"lines": 90, "functions": 90, "branches": 90, "statements": 90})
        )
        cov_json = backend_dir / "coverage.json"
        cov_json.write_text(
            json.dumps(
                {
                    "totals": {"percent_covered": 85.0},
                    "files": {
                        "src/graft/models.py": {"summary": {"percent_covered": 75.0}}
                    },
                }
            )
        )

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_backend_coverage(tmp_path)
        assert any(
            "85.0%" in violation.message and "threshold: 90%" in violation.message
            for violation in violations
        )
        assert any(
            "models.py" in violation.message and "75.0%" in violation.message
            for violation in violations
        )

    def test_no_violations_when_above_threshold(self, tmp_path, monkeypatch):
        backend_dir = tmp_path / "app" / "backend"
        backend_dir.mkdir(parents=True)
        (tmp_path / "app" / "coverage-thresholds.json").write_text(
            json.dumps({"lines": 90, "functions": 90, "branches": 90, "statements": 90})
        )
        cov_json = backend_dir / "coverage.json"
        cov_json.write_text(
            json.dumps(
                {
                    "totals": {"percent_covered": 95.0},
                    "files": {},
                }
            )
        )

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_backend_coverage(tmp_path)
        assert violations == []

    def test_handles_timeout_gracefully(self, tmp_path, monkeypatch):
        backend_dir = tmp_path / "app" / "backend"
        backend_dir.mkdir(parents=True)

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=120)

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_backend_coverage(tmp_path)
        assert violations == []


class TestRunFrontendCoverage:
    def test_returns_empty_when_frontend_dir_missing(self, tmp_path):
        violations = _mod._run_frontend_coverage(tmp_path)
        assert violations == []

    def test_returns_violations_for_metrics_below_threshold(self, tmp_path, monkeypatch):
        frontend_dir = tmp_path / "app" / "frontend"
        cov_dir = frontend_dir / "coverage"
        cov_dir.mkdir(parents=True)
        (tmp_path / "app" / "coverage-thresholds.json").write_text(
            json.dumps({"lines": 90, "functions": 90, "branches": 90, "statements": 90})
        )
        summary = cov_dir / "coverage-summary.json"
        summary.write_text(
            json.dumps(
                {
                    "total": {
                        "lines": {"pct": 88.0},
                        "functions": {"pct": 92.0},
                        "branches": {"pct": 75.0},
                        "statements": {"pct": 91.0},
                    }
                }
            )
        )

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_frontend_coverage(tmp_path)
        messages = [violation.message for violation in violations]
        assert any("lines" in message and "88.0%" in message for message in messages)
        assert any(
            "branches" in message and "75.0%" in message for message in messages
        )
        assert not any("functions" in message for message in messages)
        assert not any("statements" in message for message in messages)

    def test_no_violations_when_all_above_threshold(self, tmp_path, monkeypatch):
        frontend_dir = tmp_path / "app" / "frontend"
        cov_dir = frontend_dir / "coverage"
        cov_dir.mkdir(parents=True)
        (tmp_path / "app" / "coverage-thresholds.json").write_text(
            json.dumps({"lines": 90, "functions": 90, "branches": 90, "statements": 90})
        )
        summary = cov_dir / "coverage-summary.json"
        summary.write_text(
            json.dumps(
                {
                    "total": {
                        "lines": {"pct": 95.0},
                        "functions": {"pct": 95.0},
                        "branches": {"pct": 92.0},
                        "statements": {"pct": 95.0},
                    }
                }
            )
        )

        def fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        violations = _mod._run_frontend_coverage(tmp_path)
        assert violations == []


class TestAnalyzeFile:
    def test_python_file_dispatches_to_python_analyzer(self, tmp_path, monkeypatch):
        file_path = tmp_path / "module.py"
        file_path.write_text("print('ok')\n", encoding="utf-8")
        sentinel = _mod.FileReport(path=file_path, violations=[], info={})

        def fake_analyze_python(path, source):
            assert path == file_path
            assert "print('ok')" in source
            return sentinel

        monkeypatch.setattr(_mod, "_analyze_python", fake_analyze_python)
        assert _mod._analyze_file(file_path) is sentinel

    def test_ts_file_dispatches_to_js_like_analyzer(self, tmp_path, monkeypatch):
        file_path = tmp_path / "module.ts"
        file_path.write_text("const x = 1;\n", encoding="utf-8")
        sentinel = _mod.FileReport(path=file_path, violations=[], info={})

        def fake_analyze_js_like(path, source):
            assert path == file_path
            assert "const x = 1" in source
            return sentinel

        monkeypatch.setattr(_mod, "_analyze_js_like", fake_analyze_js_like)
        assert _mod._analyze_file(file_path) is sentinel

    def test_svelte_file_dispatches_script_only_to_js_like_analyzer(self, tmp_path, monkeypatch):
        file_path = tmp_path / "Component.svelte"
        file_path.write_text(
            textwrap.dedent(
                """
                <script lang="ts">
                const value = 1;
                </script>
                <div>{value}</div>
                """
            ),
            encoding="utf-8",
        )
        sentinel = _mod.FileReport(path=file_path, violations=[], info={})

        def fake_analyze_js_like(path, source):
            assert path == file_path
            assert "const value = 1;" in source
            assert "<div>" not in source
            return sentinel

        monkeypatch.setattr(_mod, "_analyze_js_like", fake_analyze_js_like)
        assert _mod._analyze_file(file_path) is sentinel

    def test_java_file_dispatches_to_java_analyzer(self, tmp_path, monkeypatch):
        file_path = tmp_path / "Demo.java"
        file_path.write_text("public class Demo {}\n", encoding="utf-8")
        sentinel = _mod.FileReport(path=file_path, violations=[], info={})

        def fake_analyze_java(path, source):
            assert path == file_path
            assert "public class Demo" in source
            return sentinel

        monkeypatch.setattr(_mod, "_analyze_java", fake_analyze_java)
        assert _mod._analyze_file(file_path) is sentinel

    def test_test_file_is_excluded(self, tmp_path):
        file_path = tmp_path / "test_foo.py"
        file_path.write_text("def test_x():\n    pass\n", encoding="utf-8")
        assert _mod._analyze_file(file_path) is None

    def test_nonexistent_path_returns_none(self, tmp_path):
        missing = tmp_path / "missing.py"
        assert _mod._analyze_file(missing) is None

    def test_unsupported_extension_returns_none(self, tmp_path):
        file_path = tmp_path / "data.md"
        file_path.write_text("# note\n", encoding="utf-8")
        assert _mod._analyze_file(file_path) is None


class TestFormatFollowup:
    def test_single_report_formats_file_and_violations(self):
        report = _mod.FileReport(
            path=Path("app.py"),
            violations=[_mod.Violation(message="bad thing"), _mod.Violation(message="worse thing")],
            info={"else_count": 1},
        )
        output = _mod._format_followup([report])
        assert "**Executor Quality Gate** found 2 issue(s)" in output
        assert "**app.py** (2 issues):" in output
        assert "- bad thing" in output
        assert "- worse thing" in output

    def test_multiple_reports_are_all_included(self):
        report_a = _mod.FileReport(
            path=Path("a.py"),
            violations=[_mod.Violation(message="issue a")],
            info={"else_count": 0},
        )
        report_b = _mod.FileReport(
            path=Path("b.ts"),
            violations=[_mod.Violation(message="issue b1"), _mod.Violation(message="issue b2")],
            info={"else_count": 2},
        )
        output = _mod._format_followup([report_a, report_b])
        assert "**a.py** (1 issues):" in output
        assert "**b.ts** (2 issues):" in output
        assert "- issue a" in output
        assert "- issue b1" in output
        assert "- issue b2" in output

    def test_issue_count_header_is_correct(self):
        report_a = _mod.FileReport(path=Path("a.py"), violations=[_mod.Violation(message="x")], info={})
        report_b = _mod.FileReport(path=Path("b.py"), violations=[_mod.Violation(message="y")], info={})
        output = _mod._format_followup([report_a, report_b])
        assert "**Executor Quality Gate** found 2 issue(s)" in output

    def test_else_count_info_is_included_when_present(self):
        report = _mod.FileReport(
            path=Path("logic.py"),
            violations=[_mod.Violation(message="issue")],
            info={"else_count": 3},
        )
        output = _mod._format_followup([report])
        assert "Info: `else`/`elif` count = 3" in output


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--":
        args = args[1:]
    this_file = str(Path(__file__).resolve())
    raise SystemExit(pytest.main([this_file, *(args or ["-v"])]))
