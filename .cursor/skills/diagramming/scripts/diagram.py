#!/usr/bin/env -S uv run --python 3.12
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Local Mermaid diagram helper for render, bundle, and environment checks."""

from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

FORMAT_SVG = "svg"
FORMAT_PNG = "png"
SUPPORTED_FORMATS = (FORMAT_SVG, FORMAT_PNG)

PROFILE_ASSISTANT = "assistant"
PROFILE_SHAREABLE = "shareable"
PROFILE_DIRS = {
    PROFILE_ASSISTANT: Path(".cursor") / "docs" / "diagrams",
    PROFILE_SHAREABLE: Path("docs") / "diagrams",
}

NO_RENDERER_WARNING = (
    "No renderer found. Source file created. Run 'diagram.py check' for setup."
)

PLAYWRIGHT_NOTE = (
    "playwright detected but rendering via playwright is not yet supported. "
    "Install mmdc for image rendering."
)

SCRIPT_DIR = Path(__file__).resolve().parent


def emit_json(payload: dict[str, object]) -> None:
    """Print JSON payload to stdout."""
    print(json.dumps(payload, indent=2))


def log_error(message: str) -> None:
    """Write a human-readable log line to stderr."""
    sys.stderr.write(f"{message}\n")


def make_base_result() -> dict[str, object]:
    """Create the canonical output structure."""
    return {
        "status": "ok",
        "source": None,
        "rendered": None,
        "bundle": None,
        "renderer": "none",
        "warnings": [],
    }


def fail(message: str, base: dict[str, object] | None = None) -> int:
    """Emit error JSON and return failure exit code."""
    result = base if base is not None else make_base_result()
    result["status"] = "error"
    result["error"] = message
    emit_json(result)
    log_error(message)
    return EXIT_ERROR


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments for all subcommands."""
    parser = argparse.ArgumentParser(
        prog="diagram.py",
        description="Local Mermaid diagram helper with render/bundle/check commands.",
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--profile",
        choices=[PROFILE_ASSISTANT, PROFILE_SHAREABLE],
        default=PROFILE_ASSISTANT,
        help="Output profile directory selection.",
    )
    common.add_argument(
        "--output-dir",
        type=Path,
        help="Explicit output directory override.",
    )
    common.add_argument(
        "--name",
        help="Kebab-case diagram name (required for render and bundle).",
    )
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing files.",
    )
    common.add_argument(
        "--title",
        help="Human-readable title (bundle metadata).",
    )
    common.add_argument(
        "--description",
        help="Optional description (bundle metadata).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser(
        "render",
        parents=[common],
        help="Render Mermaid source to image if renderer is available.",
    )
    render.add_argument("--input", type=Path, help="Mermaid source file path.")
    render.add_argument("--text", help="Inline Mermaid source text.")
    render.add_argument(
        "--format",
        choices=list(SUPPORTED_FORMATS),
        default=FORMAT_SVG,
        help="Rendered image format.",
    )

    bundle = subparsers.add_parser(
        "bundle",
        parents=[common],
        help="Write markdown wrapper around Mermaid source.",
    )
    bundle.add_argument("--input", type=Path, help="Mermaid source file path.")
    bundle.add_argument("--text", help="Inline Mermaid source text.")

    subparsers.add_parser(
        "check",
        help="Check local rendering prerequisites and setup hints.",
    )
    return parser.parse_args(argv)


def resolve_output_dir(args: argparse.Namespace, cwd: Path) -> Path:
    """Compute output directory from explicit override or profile."""
    if args.output_dir is not None:
        return args.output_dir
    profile_dir = PROFILE_DIRS[args.profile]
    return cwd / profile_dir


def validate_name(name: str | None) -> str:
    """Validate a required kebab-case diagram name."""
    if name is None or name.strip() == "":
        raise ValueError("--name is required for this command.")
    value = name.strip()
    if value.startswith("-") or value.endswith("-") or "--" in value:
        raise ValueError("Diagram name must be kebab-case without leading/trailing dashes.")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
    for char in value:
        if char not in allowed:
            raise ValueError("Diagram name must use lowercase letters, numbers, and dashes.")
    return value


def read_source(
    input_path: Path | None,
    text_value: str | None,
    stdin_text: str,
) -> str:
    """Read Mermaid source from exactly one input channel."""
    provided_count = 0
    if input_path is not None:
        provided_count += 1
    if text_value is not None:
        provided_count += 1
    if stdin_text != "":
        provided_count += 1

    if provided_count == 0:
        raise ValueError("Provide Mermaid input via --input, --text, or stdin.")
    if provided_count > 1:
        raise ValueError("Provide Mermaid input from exactly one source.")

    if input_path is not None:
        return input_path.read_text(encoding="utf-8")
    if text_value is not None:
        return text_value
    return stdin_text


def to_display_path(path: Path, cwd: Path) -> str:
    """Return relative display path when possible."""
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def ensure_directory(path: Path, dry_run: bool) -> None:
    """Create output directory unless dry-run is active."""
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def write_text_file(path: Path, content: str, dry_run: bool) -> None:
    """Write text content unless dry-run is active."""
    if dry_run:
        return
    path.write_text(content, encoding="utf-8")


def detect_renderer() -> str:
    """Detect best available renderer."""
    if shutil.which("mmdc"):
        return "mmdc"
    if importlib.util.find_spec("playwright") is not None:
        return "playwright"
    return "none"


def find_puppeteer_config(cwd: Path) -> Path | None:
    """Locate puppeteer config in preferred lookup order."""
    script_config = SCRIPT_DIR / "puppeteerConfig.json"
    if script_config.exists():
        return script_config
    cwd_config = cwd / "puppeteerConfig.json"
    if cwd_config.exists():
        return cwd_config
    return None


def run_mmdc(source_path: Path, output_path: Path, cwd: Path) -> tuple[bool, str]:
    """Execute mmdc renderer and return success + message."""
    assert source_path.suffix == ".mmd"
    assert output_path.suffix in (".svg", ".png")
    command = ["mmdc", "-i", str(source_path), "-o", str(output_path)]
    config_path = find_puppeteer_config(cwd)
    if config_path is not None:
        command.extend(["-p", str(config_path)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return True, ""
    message = completed.stderr.strip() or completed.stdout.strip() or "mmdc failed"
    return False, message


def humanize_name(name: str) -> str:
    """Convert kebab-case slug to title-case text."""
    words = [part for part in name.split("-") if part]
    if not words:
        return name
    return " ".join(word.capitalize() for word in words)


def first_existing_rendered_file(base_path: Path) -> Path | None:
    """Pick an existing rendered file beside source."""
    svg = base_path.with_suffix(".svg")
    if svg.exists():
        return svg
    png = base_path.with_suffix(".png")
    if png.exists():
        return png
    return None


def build_bundle_markdown(
    title: str,
    description: str | None,
    mermaid_source: str,
    image_name: str | None,
) -> str:
    """Compose shareable markdown wrapper with metadata and diagram."""
    now = datetime.now().date().isoformat()
    header = [
        "---",
        f'title: "{title}"',
        f'date: "{now}"',
        f'description: "{(description or "").replace(chr(34), chr(39))}"',
        "---",
        "",
    ]
    body = ["```mermaid", mermaid_source.rstrip(), "```", ""]
    if image_name is not None:
        body.extend([f"![{title}]({image_name})", ""])
    return "\n".join(header + body)


def windows_edge_path() -> Path:
    """Known default Microsoft Edge executable location."""
    return Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def candidate_browser_paths() -> list[Path]:
    """Return platform-specific browser candidates for puppeteer config."""
    system = platform.system().lower()
    if system == "windows":
        return [windows_edge_path()]
    if system == "linux":
        return [
            Path("/usr/bin/chromium-browser"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
        ]
    if system == "darwin":
        return [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    return []


def write_puppeteer_config_if_missing(dry_run: bool) -> tuple[Path | None, str | None]:
    """Create script-local puppeteer config when feasible."""
    config_path = SCRIPT_DIR / "puppeteerConfig.json"
    if config_path.exists():
        return config_path, None

    browser_path: Path | None = None
    for candidate in candidate_browser_paths():
        if candidate.exists():
            browser_path = candidate
            break

    if browser_path is None:
        return None, "No system Chromium/Chrome/Edge found for puppeteerConfig.json."

    payload = {"executablePath": str(browser_path)}
    if not dry_run:
        config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path, None


def install_suggestions(os_name: str) -> list[str]:
    """Return platform-specific guidance when no renderer is available."""
    shared = (
        "No renderer needed -- GitLab renders .md mermaid blocks, "
        "VS Code extensions preview .mmd files"
    )
    if os_name == "windows":
        return [
            "npm install -g @mermaid-js/mermaid-cli",
            "If mmdc browser download is blocked, set PUPPETEER_SKIP_DOWNLOAD=1 and use system Edge.",
            shared,
        ]
    if os_name == "linux":
        return [
            "npm install -g @mermaid-js/mermaid-cli",
            "pip install playwright && playwright install chromium",
            shared,
        ]
    return [
        "npm install -g @mermaid-js/mermaid-cli",
        "pip install playwright && playwright install chromium",
        shared,
    ]


def handle_render(args: argparse.Namespace, cwd: Path) -> int:
    """Implement the render subcommand."""
    result = make_base_result()
    try:
        name = validate_name(args.name)
        stdin_text = ""
        if args.input is None and args.text is None and not sys.stdin.isatty():
            stdin_text = sys.stdin.read()
        source_text = read_source(args.input, args.text, stdin_text)
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc), result)

    output_dir = resolve_output_dir(args, cwd)
    source_path = output_dir / f"{name}.mmd"
    rendered_path = output_dir / f"{name}.{args.format}"
    result["source"] = to_display_path(source_path, cwd)
    result["renderer"] = detect_renderer()

    try:
        ensure_directory(output_dir, args.dry_run)
        write_text_file(source_path, source_text.rstrip() + "\n", args.dry_run)
    except Exception as exc:  # noqa: BLE001
        return fail(f"Failed to write source file: {exc}", result)

    renderer = result["renderer"]
    warnings: list[str] = result["warnings"]  # type: ignore[assignment]
    if renderer == "none":
        warnings.append(NO_RENDERER_WARNING)
        emit_json(result)
        return EXIT_SUCCESS
    if renderer == "playwright":
        warnings.append(PLAYWRIGHT_NOTE)
        emit_json(result)
        return EXIT_SUCCESS
    if args.dry_run:
        result["rendered"] = to_display_path(rendered_path, cwd)
        emit_json(result)
        return EXIT_SUCCESS

    ok, message = run_mmdc(source_path, rendered_path, cwd)
    if ok:
        result["rendered"] = to_display_path(rendered_path, cwd)
    else:
        warnings.append(f"mmdc render failed: {message}")
    emit_json(result)
    return EXIT_SUCCESS


def handle_bundle(args: argparse.Namespace, cwd: Path) -> int:
    """Implement the bundle subcommand."""
    result = make_base_result()
    try:
        name = validate_name(args.name)
        stdin_text = ""
        if args.input is None and args.text is None and not sys.stdin.isatty():
            stdin_text = sys.stdin.read()
        source_text = read_source(args.input, args.text, stdin_text)
    except Exception as exc:  # noqa: BLE001
        return fail(str(exc), result)

    output_dir = resolve_output_dir(args, cwd)
    base_path = output_dir / name
    source_path = base_path.with_suffix(".mmd")
    bundle_path = base_path.with_suffix(".md")
    title = args.title or humanize_name(name)
    image = first_existing_rendered_file(base_path)

    result["source"] = to_display_path(source_path, cwd)
    result["bundle"] = to_display_path(bundle_path, cwd)
    markdown = build_bundle_markdown(
        title=title,
        description=args.description,
        mermaid_source=source_text,
        image_name=image.name if image is not None else None,
    )
    try:
        ensure_directory(output_dir, args.dry_run)
        write_text_file(source_path, source_text.rstrip() + "\n", args.dry_run)
        write_text_file(bundle_path, markdown, args.dry_run)
    except Exception as exc:  # noqa: BLE001
        return fail(f"Failed to write bundle files: {exc}", result)

    emit_json(result)
    return EXIT_SUCCESS


def handle_check(cwd: Path) -> int:
    """Implement the check subcommand."""
    result: dict[str, object] = {
        "status": "ok",
        "platform": platform.system(),
        "cwd": str(cwd.resolve()),
        "mmdc": shutil.which("mmdc"),
        "playwright": importlib.util.find_spec("playwright") is not None,
        "renderer": "none",
        "puppeteerConfig": None,
        "messages": [],
        "suggestions": [],
    }

    mmdc_path = result["mmdc"]
    has_playwright = bool(result["playwright"])
    messages: list[str] = result["messages"]  # type: ignore[assignment]

    if mmdc_path:
        result["renderer"] = "mmdc"
        config_path = find_puppeteer_config(cwd)
        if config_path is None:
            created_path, warning = write_puppeteer_config_if_missing(False)
            if created_path is not None:
                result["puppeteerConfig"] = str(created_path.resolve())
                messages.append("Created puppeteerConfig.json using a detected system browser.")
            else:
                messages.append(
                    warning or "Could not create puppeteerConfig.json automatically."
                )
        else:
            result["puppeteerConfig"] = str(config_path.resolve())
    elif has_playwright:
        result["renderer"] = "playwright"
        messages.append(PLAYWRIGHT_NOTE)
    else:
        os_name = platform.system().lower()
        result["suggestions"] = install_suggestions(os_name)
        messages.append("No local image renderer detected.")

    emit_json(result)
    return EXIT_SUCCESS


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    cwd = Path.cwd()
    if args.command == "render":
        return handle_render(args, cwd)
    if args.command == "bundle":
        return handle_bundle(args, cwd)
    if args.command == "check":
        return handle_check(cwd)
    log_error(f"Unknown command: {args.command}")
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
