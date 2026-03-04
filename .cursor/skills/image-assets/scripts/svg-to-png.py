#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "resvg-py==0.2.6",
#   "Pillow==11.3.0",
# ]
# ///
from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

from PIL import Image, ImageColor
import resvg_py  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]


def parse_size(size: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", size.strip())
    if match is None:
        raise argparse.ArgumentTypeError("Size must be in WxH format, for example 32x32.")
    width = int(match.group(1))
    height = int(match.group(2))
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Size values must be positive integers.")
    return width, height


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


# === SVG_RENDER_KERNEL v1 — keep in sync with icon-set.py and img-upscale.py ===


def substitute_colors(svg_text: str, fill: str, stroke: str) -> str:
    """Two-pass color substitution.

    Pass 1: inject CSS color property on root <svg> so currentColor resolves
            correctly in CSS-aware renderers.
    Pass 2: replace explicit fill/stroke="currentColor" attributes for renderers
            that do not process CSS.
    """
    # Pass 1: inject or update style="color: {fill}" on root <svg> element
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

    # Pass 2: explicit attribute replacement
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


# === END SVG_RENDER_KERNEL v1 ===


def render_svg_to_image(svg_text: str, width: int, height: int, fit: str) -> Image.Image:
    """Render SVG to RGBA PIL Image at the requested pixel dimensions.

    fit='contain': preserve aspect ratio, letterbox transparent (resvg default).
    fit='cover': fill target fully, clip edges. Achieved by injecting
                 preserveAspectRatio='xMidYMid slice' into the SVG root.
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


def resolve_background_rgba(background: str) -> tuple[int, int, int, int]:
    if background.lower() == "transparent":
        return (0, 0, 0, 0)
    rgba = ImageColor.getcolor(background, "RGBA")
    if not isinstance(rgba, tuple):
        return (rgba, rgba, rgba, 255)
    return (int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3]))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert SVG to PNG with optional color replacement, padding, and background."
    )
    parser.add_argument("input_svg", type=Path, help="Input SVG file path.")
    parser.add_argument("output_png", type=Path, help="Output PNG file path.")
    parser.add_argument("--size", default="32x32", help="Output size in WxH format. Default: 32x32.")
    parser.add_argument(
        "--fill",
        default="#000000",
        type=lambda value: parse_color(value),
        help="Color used to replace fill='currentColor'. Default: #000000.",
    )
    parser.add_argument(
        "--stroke",
        type=lambda value: parse_color(value),
        help="Color used to replace stroke='currentColor'. Defaults to --fill.",
    )
    parser.add_argument(
        "--background",
        default="transparent",
        type=lambda value: parse_color(value, allow_transparent=True),
        help="Background color or 'transparent'. Default: transparent.",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=0,
        help="Padding in pixels around rendered icon. Default: 0.",
    )
    parser.add_argument(
        "--fit",
        choices=["contain", "cover"],
        default="contain",
        help="Aspect ratio handling when viewBox is not square. 'contain' letterboxes (default); 'cover' fills and clips.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.input_svg.is_file():
        parser.error(f"Input SVG does not exist: {args.input_svg}")
    if args.padding < 0:
        parser.error(f"--padding must be >= 0, got {args.padding}.")

    width, height = parse_size(args.size)
    inner_width = width - (2 * args.padding)
    inner_height = height - (2 * args.padding)
    if inner_width <= 0 or inner_height <= 0:
        parser.error(
            f"--padding {args.padding} is too large for --size {args.size}: "
            f"inner dimensions would be {inner_width}x{inner_height} (must be > 0)."
        )

    stroke_color = args.stroke or args.fill
    svg_text = args.input_svg.read_text(encoding="utf-8")
    svg_text = substitute_colors(svg_text, args.fill, stroke_color)

    rendered = render_svg_to_image(svg_text, inner_width, inner_height, args.fit)
    canvas = Image.new("RGBA", (width, height), resolve_background_rgba(args.background))
    canvas.alpha_composite(rendered, (args.padding, args.padding))

    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output_png, format="PNG", optimize=True)
    print(f"Written: {args.output_png} ({width}x{height})")


if __name__ == "__main__":
    main()
