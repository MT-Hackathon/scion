#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "vtracer",
#   "resvg-py==0.2.6",
#   "Pillow==11.3.0",
# ]
# ///
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

from PIL import Image
import resvg_py  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
import vtracer  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]

MAX_IMAGE_SIZE = 8192
DEFAULT_SIZE = "1024x1024"


def parse_size(size: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", size.strip())
    if match is None:
        raise argparse.ArgumentTypeError("Size must be in WxH format, for example 32x32.")
    width = int(match.group(1))
    height = int(match.group(2))
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Size values must be positive integers.")
    return width, height


def validate_input(path: Path, parser: argparse.ArgumentParser) -> Image.Image:
    if not path.is_file():
        parser.error(f"Input PNG does not exist: {path}")
    try:
        image = Image.open(path)
    except OSError as exc:
        parser.error(f"Input is not a readable image: {path} ({exc})")
    if image.format != "PNG":
        image.close()
        parser.error(f"Input must be a PNG file: {path}")
    width, height = image.size
    if width > MAX_IMAGE_SIZE or height > MAX_IMAGE_SIZE:
        image.close()
        parser.error(
            f"Input PNG exceeds max size {MAX_IMAGE_SIZE}px per dimension: {width}x{height}"
        )
    return image


# === SVG_RENDER_KERNEL v1 — keep in sync with icon-set.py and svg-to-png.py ===


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


def upscale_vectorize(input_path: Path, width: int, height: int) -> Image.Image:
    svg_text = vtracer.convert_to_svg(str(input_path), colormode="color")
    return render_svg_to_image(svg_text, width, height, fit="contain")


def _to_pil_image(result: object) -> Image.Image:
    if isinstance(result, tuple) and result:
        result = result[0]
    if isinstance(result, Image.Image):
        return result.convert("RGBA")
    try:
        return Image.fromarray(result).convert("RGBA")  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - defensive runtime path
        raise SystemExit(f"error: unsupported AI upscaler output type: {type(result)!r}") from exc


def _probe_upscaler_method(upscaler: object, method_name: str, image: Image.Image) -> Image.Image | None:
    method = getattr(upscaler, method_name, None)
    if not callable(method):
        return None
    try:
        return _to_pil_image(method(image))
    except TypeError:
        return None


def upscale_ai(input_path: Path, width: int, height: int) -> Image.Image:
    try:
        from realesrgan_ncnn_py import RealESRGAN  # type: ignore[import-not-found]
    except ImportError:
        print(
            "ai mode requires realesrgan-ncnn-py. Install with: uv pip install realesrgan-ncnn-py"
        )
        sys.exit(1)

    upscaler = RealESRGAN(gpuid=-1, model="animevideov3")
    with Image.open(input_path) as src:
        input_image = src.convert("RGB")

    output: Image.Image | None = None
    for method_name in ("process", "predict", "enhance"):
        output = _probe_upscaler_method(upscaler, method_name, input_image)
        if output is not None:
            break
    if output is None and callable(upscaler):
        output = _to_pil_image(upscaler(input_image))
    if output is None:
        raise SystemExit("error: RealESRGAN did not return an image result.")

    if output.size != (width, height):
        output = output.resize((width, height), Image.Resampling.LANCZOS)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upscale a raster PNG using vector tracing or AI super-resolution."
    )
    parser.add_argument("input", type=Path, help="Input PNG file path.")
    parser.add_argument("output", type=Path, help="Output PNG file path.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help=f"Target output size in WxH. Default: {DEFAULT_SIZE}.")
    parser.add_argument(
        "--mode",
        choices=["vectorize", "ai"],
        default="vectorize",
        help="Upscale strategy. 'vectorize' traces to SVG, 'ai' uses RealESRGAN.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    width, height = parse_size(args.size)

    probe = validate_input(args.input, parser)
    probe.close()

    if args.mode == "ai":
        output_image = upscale_ai(args.input, width, height)
    else:
        output_image = upscale_vectorize(args.input, width, height)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output_image.save(args.output, format="PNG", optimize=True)
    output_image.close()
    print(f"Written: {args.output} ({width}x{height})")


if __name__ == "__main__":
    main()
