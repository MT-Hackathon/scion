#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "resvg-py==0.2.6",
#   "Pillow==11.3.0",
#   "icnsutil==1.1.0",
# ]
# ///
from __future__ import annotations

import argparse
import hashlib
import io
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

import resvg_py  # pyright: ignore[reportMissingImports]
from PIL import Image, ImageColor
import icnsutil  # pyright: ignore[reportMissingImports]

MASTER_SIZE = 1024
TRAY_SIZE = 32
PRIMARY_OUTPUT_SIZES: tuple[tuple[str, int], ...] = (
    ("icon.png", MASTER_SIZE),
    ("32x32.png", 32),
    ("128x128.png", 128),
    ("128x128@2x.png", 256),
)
TRAY_OUTPUT_FILENAMES: tuple[tuple[str, str], ...] = (
    ("tray-synced.png", "synced"),
    ("tray-drifted.png", "drifted"),
    ("tray-error.png", "error"),
)
ICO_FILENAME = "icon.ico"
ICNS_FILENAME = "icon.icns"
TOTAL_OUTPUT_COUNT = len(PRIMARY_OUTPUT_SIZES) + len(TRAY_OUTPUT_FILENAMES) + 2
ICO_SIZES = [16, 24, 32, 48, 64, 256]
ICNS_BASE_SIZES = [16, 32, 128, 256, 512]


class IconSpec(NamedTuple):
    filename: str
    width: int
    height: int
    fill_key: str  # "primary" or "synced"/"drifted"/"error"


def parse_color(color: str | None, *, allow_transparent: bool = False) -> str:
    if color is None:
        raise argparse.ArgumentTypeError("Color value is required.")
    value = color.strip()
    if allow_transparent and value.lower() in {"transparent", "none"}:
        return "transparent"
    try:
        ImageColor.getcolor(value, "RGBA")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid color value: {color}") from exc
    return value


def resolve_background_rgba(background: str) -> tuple[int, int, int, int]:
    if background.lower() == "transparent":
        return (0, 0, 0, 0)
    rgba = ImageColor.getcolor(background, "RGBA")
    if not isinstance(rgba, tuple):
        return (rgba, rgba, rgba, 255)
    return (int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3]))


# === SVG_RENDER_KERNEL v1 — keep in sync with svg-to-png.py ===

def substitute_colors(svg_text: str, fill: str, stroke: str) -> str:
    """Two-pass color substitution.

    Pass 1: inject CSS color property on root <svg> so currentColor resolves
            correctly in CSS-aware renderers.
    Pass 2: replace explicit fill/stroke="currentColor" attributes for renderers
            that do not process CSS.
    """
    def _inject_color(m: re.Match) -> str:
        tag = m.group(0)
        style_match = re.search(r'\bstyle\s*=\s*(["\'])(.*?)\1', tag)
        if style_match:
            existing = style_match.group(2)
            new_style = re.sub(r'\bcolor\s*:[^;]+;?', "", existing).strip("; ")
            new_style = f"color: {fill}; {new_style}".strip("; ")
            return tag[: style_match.start()] + f'style="{new_style}"' + tag[style_match.end() :]
        return tag.rstrip(">").rstrip("/").rstrip() + f' style="color: {fill}">'

    svg_text = re.sub(r"<svg\b[^>]*>", _inject_color, svg_text, count=1)

    svg_text = re.sub(
        r'(fill\s*=\s*[\'"])currentColor([\'"])',
        rf"\g<1>{fill}\2",
        svg_text,
        flags=re.IGNORECASE,
    )
    svg_text = re.sub(
        r'(stroke\s*=\s*[\'"])currentColor([\'"])',
        rf"\g<1>{stroke}\2",
        svg_text,
        flags=re.IGNORECASE,
    )
    return svg_text


def render_svg(svg_text: str, width: int, height: int, fit: str) -> Image.Image:
    """Render SVG to RGBA PIL Image.

    fit='contain': preserve aspect ratio, letterbox transparent (resvg default).
    fit='cover': fill target fully, clip edges.
    """
    if fit == "cover":
        svg_text = re.sub(
            r"(<svg\b[^>]*?)\s*/?>",
            lambda m: re.sub(r'\bpreserveAspectRatio\s*=\s*["\'][^"\']*["\']', "", m.group(0)).rstrip(">").rstrip("/").rstrip()
            + ' preserveAspectRatio="xMidYMid slice">',
            svg_text,
            count=1,
        )
    png_bytes = resvg_py.svg_to_bytes(svg_string=svg_text, width=width, height=height)
    with Image.open(io.BytesIO(png_bytes)) as img:
        rendered = img.convert("RGBA")
    if rendered.size != (width, height):
        rendered = rendered.resize((width, height), Image.Resampling.LANCZOS)
    return rendered

# === END SVG_RENDER_KERNEL v1 ===


def build_ico(master: Image.Image, output_path: Path) -> None:
    """Build multi-size ICO from a 1024x1024 RGBA master."""
    master.save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )


def build_icns(master: Image.Image, output_path: Path) -> None:
    """Build macOS .icns from a 1024x1024 RGBA master."""
    # Sizes: [16,32,128,256,512] at 1x; [32,64,256,512,1024] at 2x (same pixels as 1x@2x)
    icns_file = icnsutil.IcnsFile()
    with tempfile.TemporaryDirectory() as tmp:
        for size in ICNS_BASE_SIZES:
            img = master.resize((size, size), Image.Resampling.LANCZOS)
            p = Path(tmp) / f"icon_{size}x{size}.png"
            img.save(p, format="PNG")
            icns_file.add_media(file=str(p))
            # 2x: same pixel count as double (e.g., 32x32 represents 16x16@2x)
            if size <= 512:
                size2x = size * 2
                img2x = master.resize((size2x, size2x), Image.Resampling.LANCZOS)
                p2x = Path(tmp) / f"icon_{size}x{size}@2x.png"
                img2x.save(p2x, format="PNG")
                icns_file.add_media(file=str(p2x))
    icns_file.write(str(output_path))


def sha256_file(path: Path) -> str | None:
    """Return hex digest of file, or None if file does not exist."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the full Tauri icon set from a single source SVG."
    )
    parser.add_argument("input_svg", type=Path, help="Source SVG file.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to write output files.")
    parser.add_argument("--fill", default="#000000", type=parse_color, help="Primary icon fill color. Default: #000000.")
    parser.add_argument("--background", default="transparent", type=lambda v: parse_color(v, allow_transparent=True), help="Background color or 'transparent'. Default: transparent.")
    parser.add_argument("--fit", choices=["contain", "cover"], default="contain", help="Aspect ratio handling. Default: contain.")
    parser.add_argument("--tray-fill-synced", default="#22c55e", type=parse_color, dest="tray_fill_synced", help="Tray icon fill for synced state. Default: #22c55e.")
    parser.add_argument("--tray-fill-drifted", default="#f59e0b", type=parse_color, dest="tray_fill_drifted", help="Tray icon fill for drifted state. Default: #f59e0b.")
    parser.add_argument("--tray-fill-error", default="#ef4444", type=parse_color, dest="tray_fill_error", help="Tray icon fill for error state. Default: #ef4444.")
    parser.add_argument("--tray-background", default="transparent", type=lambda v: parse_color(v, allow_transparent=True), dest="tray_background", help="Tray icon background. Default: transparent.")
    parser.add_argument("--check", action="store_true", help="Validate committed icons against what would be generated. No files written.")
    return parser


def _run_check(
    output_dir: Path,
    master: Image.Image,
    png_outputs: list[tuple[str, Image.Image | None]],
    args: argparse.Namespace,
) -> None:
    """Compare generated hashes against committed files. Exit 1 if any differ."""
    mismatches: list[str] = []

    print("Check results:")
    print(f"  {'STATUS':8s} FILE")

    for filename, img in png_outputs:
        if img is None:
            raise RuntimeError(f"Internal error: generated PNG image is missing for {filename}")
        committed = output_dir / filename
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        generated_hash = sha256_bytes(buf.getvalue())
        committed_hash = sha256_file(committed)
        status = "OK" if committed_hash == generated_hash else ("MISSING" if committed_hash is None else "STALE")
        print(f"  {status:8s} {filename}")
        if status != "OK":
            mismatches.append(f"{filename}: {status}")

    # ICO and ICNS: write to temp dir for comparison
    with tempfile.TemporaryDirectory() as tmp:
        tmp_ico = Path(tmp) / ICO_FILENAME
        build_ico(master, tmp_ico)
        ico_hash = sha256_bytes(tmp_ico.read_bytes())
        committed_ico_hash = sha256_file(output_dir / ICO_FILENAME)
        status = "OK" if ico_hash == committed_ico_hash else ("MISSING" if committed_ico_hash is None else "STALE")
        print(f"  {status:8s} {ICO_FILENAME}")
        if status != "OK":
            mismatches.append(f"{ICO_FILENAME}: {status}")

        tmp_icns = Path(tmp) / ICNS_FILENAME
        build_icns(master, tmp_icns)
        icns_hash = sha256_bytes(tmp_icns.read_bytes())
        committed_icns_hash = sha256_file(output_dir / ICNS_FILENAME)
        status = "OK" if icns_hash == committed_icns_hash else ("MISSING" if committed_icns_hash is None else "STALE")
        print(f"  {status:8s} {ICNS_FILENAME}")
        if status != "OK":
            mismatches.append(f"{ICNS_FILENAME}: {status}")

    if mismatches:
        print(f"\n{len(mismatches)} file(s) are stale or missing. Run icon-set.py without --check to regenerate.")
        for mismatch in mismatches:
            print(f"  - {mismatch}")
        raise SystemExit(1)
    print("\nAll icon files are current.")


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.input_svg.exists():
        parser.error(f"--input_svg constraint violated: input file does not exist: {args.input_svg}")
    if not args.input_svg.is_file():
        parser.error(f"--input_svg constraint violated: path is not a file: {args.input_svg}")
    if args.output_dir.exists() and not args.output_dir.is_dir():
        parser.error(f"--output-dir constraint violated: path exists but is not a directory: {args.output_dir}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    _validate_args(parser, args)

    try:
        svg_text = args.input_svg.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        parser.error(f"--input_svg constraint violated: file must be UTF-8 text SVG: {args.input_svg} ({exc})")
    except OSError as exc:
        parser.error(f"--input_svg constraint violated: failed to read input file: {args.input_svg} ({exc})")

    bg_rgba = resolve_background_rgba(args.background)
    tray_bg_rgba = resolve_background_rgba(args.tray_background)

    # Render primary icon at master size; derive all smaller sizes from it
    primary_svg = substitute_colors(svg_text, args.fill, args.fill)
    master = render_svg(primary_svg, MASTER_SIZE, MASTER_SIZE, args.fit)

    def make_primary(size: int) -> Image.Image:
        canvas = Image.new("RGBA", (size, size), bg_rgba)
        icon = master.resize((size, size), Image.Resampling.LANCZOS)
        canvas.alpha_composite(icon)
        return canvas

    def make_tray(fill: str) -> Image.Image:
        tray_svg = substitute_colors(svg_text, fill, fill)
        rendered = render_svg(tray_svg, TRAY_SIZE, TRAY_SIZE, args.fit)
        canvas = Image.new("RGBA", (TRAY_SIZE, TRAY_SIZE), tray_bg_rgba)
        canvas.alpha_composite(rendered)
        return canvas

    fill_map = {
        "primary": args.fill,
        "synced": args.tray_fill_synced,
        "drifted": args.tray_fill_drifted,
        "error": args.tray_fill_error,
    }
    specs: list[IconSpec] = [
        IconSpec("icon.png", MASTER_SIZE, MASTER_SIZE, "primary"),
        IconSpec("32x32.png", 32, 32, "primary"),
        IconSpec("128x128.png", 128, 128, "primary"),
        IconSpec("128x128@2x.png", 256, 256, "primary"),
        IconSpec("tray-synced.png", TRAY_SIZE, TRAY_SIZE, "synced"),
        IconSpec("tray-drifted.png", TRAY_SIZE, TRAY_SIZE, "drifted"),
        IconSpec("tray-error.png", TRAY_SIZE, TRAY_SIZE, "error"),
    ]

    outputs: list[tuple[str, Image.Image | None]] = []
    for spec in specs:
        if spec.fill_key == "primary":
            outputs.append((spec.filename, make_primary(spec.width)))
            continue
        outputs.append((spec.filename, make_tray(fill_map[spec.fill_key])))

    if args.check:
        _run_check(args.output_dir, master, outputs, args)
        return

    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        parser.error(f"--output-dir constraint violated: unable to create directory: {args.output_dir} ({exc})")

    for filename, img in outputs:
        if img is None:
            raise RuntimeError(f"Internal error: generated image is missing for {filename}")
        path = args.output_dir / filename
        img.save(path, format="PNG", optimize=True)
        print(f"  Written: {path}")

    ico_path = args.output_dir / ICO_FILENAME
    build_ico(master, ico_path)
    print(f"  Written: {ico_path}")

    icns_path = args.output_dir / ICNS_FILENAME
    build_icns(master, icns_path)
    print(f"  Written: {icns_path}")

    print(f"\nDone. {TOTAL_OUTPUT_COUNT} files written to {args.output_dir}")


if __name__ == "__main__":
    main()
