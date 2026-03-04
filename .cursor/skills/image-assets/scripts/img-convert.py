#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "Pillow==11.3.0",
#   "pyoxipng==9.1.1",
#   "piexif==1.1.3",
# ]
# ///
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import piexif  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
from PIL import Image, ImageColor, ImageOps

import oxipng  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]

MAX_IMAGE_SIZE = 8192  # pixels per dimension — reject inputs exceeding this
LOSSY_FORMATS = {"jpg", "jpeg", "webp", "avif"}
DEFAULT_QUALITY = 85
ICO_SIZES = [16, 32, 48, 64, 128, 256]
SUPPORTED_OUTPUT_FORMATS = ("png", "jpg", "webp", "avif", "ico")
EXIF_STRIP_FORMATS = {"jpg", "jpeg", "webp"}
JPEG_BACKGROUND = (255, 255, 255)

FORMAT_SAVE_KWARGS: dict[str, dict] = {
    "png": {"format": "PNG", "optimize": True},
    "jpg": {"format": "JPEG", "quality": DEFAULT_QUALITY},
    "jpeg": {"format": "JPEG", "quality": DEFAULT_QUALITY},
    "webp": {"format": "WEBP", "quality": DEFAULT_QUALITY},
    "avif": {"format": "AVIF", "quality": DEFAULT_QUALITY},
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert, optimize, resize, or tint raster images.")
    parser.add_argument("input", type=Path, help="Source image file.")
    parser.add_argument("--output", type=Path, help="Output file path. Default: <input>.<format> in same directory.")
    parser.add_argument(
        "--format",
        choices=["png", "jpg", "webp", "avif", "ico"],
        dest="fmt",
        help="Output format. Default: same as input.",
    )
    parser.add_argument("--quality", type=int, help="Lossy encoding quality 0–100. Default: 85. Requires --allow-lossy.")
    parser.add_argument("--width", type=int, help="Resize width in pixels. Requires --allow-lossy.")
    parser.add_argument("--height", type=int, help="Resize height in pixels. Requires --allow-lossy.")
    parser.add_argument("--optimize", action="store_true", help="Lossless PNG optimization.")
    parser.add_argument("--strip-exif", action="store_true", dest="strip_exif", help="Strip EXIF metadata.")
    parser.add_argument("--tint", type=str, help="Apply color tint (e.g. '#ff0000').")
    parser.add_argument(
        "--allow-lossy",
        action="store_true",
        dest="allow_lossy",
        help="Allow quality-reducing operations.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=MAX_IMAGE_SIZE,
        dest="max_size",
        help=f"Reject inputs exceeding this pixel dimension. Default: {MAX_IMAGE_SIZE}.",
    )
    return parser


def normalize_format(raw_format: str) -> str:
    normalized = raw_format.lower().lstrip(".")
    if normalized == "jpeg":
        return "jpg"
    return normalized


def detect_input_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if not suffix:
        supported = ", ".join(SUPPORTED_OUTPUT_FORMATS)
        raise SystemExit(
            f"error: input format is unknown for {path.name}. "
            f"Set --format explicitly. Supported formats: {supported}."
        )

    normalized = normalize_format(suffix)
    if normalized not in SUPPORTED_OUTPUT_FORMATS:
        supported = ", ".join(SUPPORTED_OUTPUT_FORMATS)
        raise SystemExit(
            f"error: input extension '.{suffix}' is not recognized. "
            f"Set --format explicitly. Supported formats: {supported}."
        )
    return normalized


def resolve_output_path(input_path: Path, output_path: Path | None, output_format: str) -> Path:
    if output_path is not None:
        return output_path
    return input_path.with_name(f"{input_path.stem}.{output_format}")


def requires_lossy(args: argparse.Namespace, output_format: str) -> bool:
    if output_format in LOSSY_FORMATS:
        return True
    if args.quality is not None:
        return True
    if args.width is not None or args.height is not None:
        return True
    return False


def check_image_dimensions(path: Path, max_size: int) -> None:
    """Reject images that would exhaust memory when loaded as pixels."""
    with Image.open(path) as probe:
        w, h = probe.size
    if w > max_size or h > max_size:
        raise SystemExit(
            f"error: {path.name} is {w}x{h}, exceeds --max-size {max_size}. "
            f"Use --max-size to raise the limit if intentional."
        )


def compute_resize(original: tuple[int, int], width: int | None, height: int | None) -> tuple[int, int]:
    """Compute output size preserving aspect ratio when only one dimension is given."""
    ow, oh = original
    if width is not None and height is not None:
        return (width, height)
    if width is not None:
        return (width, round(oh * width / ow))
    if height is not None:
        return (round(ow * height / oh), height)
    return original


def strip_exif(data: bytes) -> bytes:
    """Remove all EXIF metadata from JPEG/WebP bytes without re-encoding."""
    buf = io.BytesIO()
    piexif.remove(data, buf)
    return buf.getvalue()


def apply_tint(img: Image.Image, color: str) -> Image.Image:
    """Colorize image by mapping its luminosity to a color gradient."""
    return ImageOps.colorize(img.convert("L"), black="black", white=color).convert("RGBA")


def optimize_png(data: bytes) -> bytes:
    """Lossless PNG optimization using pyoxipng."""
    return oxipng.optimize_from_memory(data, level=2)


def save_ico(img: Image.Image, output_path: Path, quality: int) -> None:
    """Save image as multi-size ICO. Quality arg is ignored (ICO is lossless)."""
    _ = quality
    img.save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )


def ensure_valid_args(args: argparse.Namespace, output_format: str) -> None:
    if args.max_size <= 0:
        raise SystemExit(f"error: --max-size must be a positive integer, got {args.max_size}.")
    if args.quality is not None and not 0 <= args.quality <= 100:
        raise SystemExit(f"error: --quality must be between 0 and 100, got {args.quality}.")
    if args.width is not None and args.width <= 0:
        raise SystemExit(f"error: --width must be a positive integer, got {args.width}.")
    if args.height is not None and args.height <= 0:
        raise SystemExit(f"error: --height must be a positive integer, got {args.height}.")
    if args.tint is not None:
        try:
            ImageColor.getcolor(args.tint, "RGBA")
        except ValueError as exc:
            raise SystemExit(f"error: --tint must be a valid color, got {args.tint!r}.") from exc

    if requires_lossy(args, output_format) and not args.allow_lossy:
        if output_format in LOSSY_FORMATS:
            raise SystemExit(
                f"error: --format {output_format} produces lossy output. "
                "Pass --allow-lossy to confirm quality reduction is intended."
            )
        if args.quality is not None:
            raise SystemExit(
                "error: --quality may reduce output fidelity. "
                "Pass --allow-lossy to confirm quality reduction is intended."
            )
        raise SystemExit(
            "error: resizing with --width/--height discards pixel data. "
            "Pass --allow-lossy to confirm quality reduction is intended."
        )

    if args.optimize and output_format != "png":
        print(
            f"warning: --optimize is PNG-only and will be skipped for --format {output_format}.",
            file=sys.stderr,
        )
    if args.strip_exif and output_format not in EXIF_STRIP_FORMATS:
        print(
            f"warning: --strip-exif is only meaningful for JPEG/WebP and will be skipped for --format {output_format}.",
            file=sys.stderr,
        )
    if args.quality is not None and output_format not in LOSSY_FORMATS:
        print(
            f"warning: --quality is ignored for --format {output_format}.",
            file=sys.stderr,
        )


def prepare_for_format(image: Image.Image, output_format: str) -> Image.Image:
    if output_format == "jpg":
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, JPEG_BACKGROUND)
            background.paste(image, mask=image.getchannel("A"))
            return background
        return image.convert("RGB")
    if output_format in {"png", "webp", "avif", "ico"}:
        if image.mode in {"RGB", "RGBA"}:
            return image
        return image.convert("RGBA")
    return image


def encode_image(image: Image.Image, output_format: str, quality: int | None) -> bytes:
    save_kwargs = dict(FORMAT_SAVE_KWARGS[output_format])
    if quality is not None and output_format in LOSSY_FORMATS:
        save_kwargs["quality"] = quality
    buf = io.BytesIO()
    image.save(buf, **save_kwargs)
    return buf.getvalue()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"error: input file does not exist: {args.input}")

    output_format = args.fmt or detect_input_format(args.input)
    output_path = resolve_output_path(args.input, args.output, output_format)
    ensure_valid_args(args, output_format)

    check_image_dimensions(args.input, args.max_size)

    try:
        with Image.open(args.input) as src:
            img = src.copy()
    except OSError as exc:
        raise SystemExit(f"error: failed to open image '{args.input}': {exc}") from exc

    if args.tint is not None:
        img = apply_tint(img, args.tint)

    target_size = compute_resize(img.size, args.width, args.height)
    if target_size != img.size:
        img = img.resize(target_size, Image.Resampling.LANCZOS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    quality = args.quality if args.quality is not None else DEFAULT_QUALITY

    if output_format == "ico":
        save_ico(prepare_for_format(img, "ico"), output_path, quality)
    else:
        prepared = prepare_for_format(img, output_format)
        data = encode_image(prepared, output_format, args.quality)

        if args.strip_exif and output_format in EXIF_STRIP_FORMATS:
            try:
                data = strip_exif(data)
            except Exception as exc:  # pragma: no cover - defensive runtime path
                raise SystemExit(f"error: failed to strip EXIF metadata: {exc}") from exc

        if args.optimize and output_format == "png":
            try:
                data = optimize_png(data)
            except Exception as exc:  # pragma: no cover - defensive runtime path
                raise SystemExit(f"error: PNG optimization failed: {exc}") from exc

        output_path.write_bytes(data)

    final_width, final_height = img.size
    print(f"Written: {output_path} ({final_width}x{final_height}, {output_format})")


if __name__ == "__main__":
    main()
