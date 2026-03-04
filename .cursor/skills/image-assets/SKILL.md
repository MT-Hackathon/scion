---
name: image-assets
description: "Governs programmatic image and asset processing: SVG-to-PNG rendering, ICO/ICNS generation, color substitution, format conversion, and batch icon set generation. Use when converting SVG logos to icon PNGs, generating multi-size ICO/ICNS files, substituting fill colors in icon variants, or producing full platform icon sets from a single SVG source. DO NOT use for AI-generated original concepts (see image-generation), Mermaid diagram generation (see diagramming), or UI mockups."
---

<ANCHORSKILL-IMAGE-ASSETS>

# Image Assets

Programmatic rendering and conversion for icons, logos, and raster assets. SVG is the source of truth; all derived formats are produced by script.

## Table of Contents

- [Tool Stack](#tool-stack)
- [Core Concepts](#core-concepts)
- [Capability Matrix](#capability-matrix)
- [Script Reference](#script-reference)
- [Security](#security)
- [Anti-Patterns](#anti-patterns)
- [Cross-References](#cross-references)

## Tool Stack

Every library ships as a pre-compiled wheel — no system library installation required on any platform. Portability is the selection criterion, not feature breadth.

| Library | Role | Why this, not X |
|---------|------|-----------------|
| `resvg-py` | SVG renderer | Rust `resvg` compiled into the wheel. Zero system deps. `cairosvg` requires native Cairo DLLs (hostile on Windows) and is not used. |
| `Pillow` ≥ 11.3 | Raster manipulation | Resize, crop, composite, color ops, ICO container, WebP/AVIF — AVIF support bundled, no `libavif` system dep. |
| `icnsutil` | macOS `.icns` generation | Pure Python. Pillow cannot write ICNS; `iconutil` is macOS-only. |
| `pyoxipng` | PNG optimization | Rust `oxipng` via Python bindings. Lossless size reduction post-render. |
| `piexif` | EXIF metadata | Pure Python. Read or strip EXIF before publishing or serving images. |
| `vtracer` | Raster-to-SVG tracer | Rust binary compiled into wheel. Zero system deps. Traces flat/icon PNGs to clean vector SVG using hierarchical color clustering. Best-in-class for geometric flat art; `potrace` is monochrome-only. |
| `realesrgan-ncnn-py` | AI super-resolution (CPU) | NCNN inference engine — runs on CPU with no CUDA installation. Uses `animevideov3` model, which is optimized for flat synthetic images. Not in PEP 723 header (install separately for `--mode ai`). |

## Core Concepts

**SVG is the source of truth.** All icon and logo variants — size, color, format — are derived from the canonical SVG at render time. Never maintain separate source files per color or size. Outputs are disposable; the SVG and the invocation are the artifact.

**Programmatic rendering for logos; `GenerateImage` for original concepts.** Use scripts to produce variants of an *existing* logo or icon. AI generation cannot reproduce exact logo geometry — it must never be used for logo variants.

**Color substitution is a source-level operation.** SVG renderers resolve attributes at parse time. Substitute fill/stroke values in the SVG source string before passing to the renderer — downstream tools see a fully resolved SVG.

**Dual-pass color substitution is the correct pattern.** Color replacement runs in two passes: (1) inject `style="color: {fill}"` on the root `<svg>` element so CSS-aware renderers resolve `currentColor` correctly; (2) regex-replace explicit `fill="currentColor"` and `stroke="currentColor"` attributes for non-CSS renderers. Both passes run always. `resvg` defaults `currentColor` to black when no CSS context — pass 1 is belt-and-suspenders against that. The `SVG_RENDER_KERNEL v1` block in `svg-to-png.py`, `icon-set.py`, and `img-upscale.py` implements this and is intentionally duplicated for PEP 723 portability — keep all three copies in sync.

**viewBox governs scale.** Pass target pixel dimensions to the renderer; never manually crop or stretch. A 200-unit `viewBox` with `stroke-width: 3` renders at ~0.42px at 32px output — effectively invisible. Keep `viewBox` ≤ 100 units or scale `stroke-width` proportionally for small icon targets.

**Small-icon legibility is a geometry problem, not a script problem.** A detailed mark at 16/24px may be illegible regardless of render quality. A 5:7 portrait viewBox (e.g., 100×140) produces a mark of approximately 11×16px at 16px output — branch detail disappears. Design a micro-variant SVG for tiny targets and pass it as the source; do not expect a complex logo to remain legible below ~32px.

**LANCZOS for quality resizing.** When Pillow is used for post-render resize, always use `Image.Resampling.LANCZOS`. It is the highest-quality downsampling filter.

**Large asset rendering uses the SVG path, not upscaling.** When the source is an SVG, always render at target dimensions directly via `svg-to-png.py --size`. SVG is resolution-independent — a 4000px render is identical in quality to the 32px icon. Never upscale a raster derived from an SVG when the original SVG is available. The raster upscale path (`img-upscale.py`) exists for assets with no SVG origin.

**LANCZOS has a practical ceiling for upscaling.** Pillow's LANCZOS is the correct filter for downscaling and small upscales up to ~2x. Beyond 2x, upscaling with LANCZOS produces visible blurring and edge-haloing artifacts on sharp geometric art. Use `img-upscale.py` for any upscale exceeding 2x.

## Capability Matrix

| Capability | Script | Libraries |
|-----------|--------|-----------|
| SVG → PNG with color substitution | `svg-to-png.py` | `resvg-py`, `Pillow` |
| One SVG → full Tauri + platform icon set | `icon-set.py` | `resvg-py`, `Pillow`, `icnsutil` |
| CI staleness check for committed icons | `icon-set.py --check` | — |
| Format conversion: PNG ↔ JPG, WebP, AVIF, ICO | `img-convert.py` | `Pillow` |
| PNG optimization (lossless) | `img-convert.py --optimize` | `pyoxipng` |
| Color tinting / desaturation | `img-convert.py --tint` | `Pillow` |
| EXIF strip / read | `img-convert.py --strip-exif` | `Pillow`, `piexif` |
| PNG → large PNG via vectorize or AI SR | `img-upscale.py` | `vtracer`, `resvg-py`, `Pillow` (vectorize); `realesrgan-ncnn-py`, `Pillow` (ai) |

## Script Reference

### svg-to-png.py

Renders one SVG to one PNG with optional color substitution, padding, and background.

```bash
uv run .cursor/skills/image-assets/scripts/svg-to-png.py \
  src-tauri/icons/graftmark.svg \
  src-tauri/icons/tray-icon-white.png \
  --size 32x32 \
  --fill "#ffffff" \
  --stroke "#ffffff" \
  --background transparent \
  --padding 2
```

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `input_svg` | Yes | — | Source SVG file (positional) |
| `output_png` | Yes | — | Output PNG file path (positional) |
| `--size <WxH>` | No | `32x32` | Output pixel dimensions |
| `--fill <color>` | No | `#000000` | Fill color for `currentColor` substitution |
| `--stroke <color>` | No | same as `--fill` | Stroke color for `currentColor` substitution |
| `--background <color>` | No | `transparent` | Background fill. Accepts hex or `transparent` |
| `--padding <px>` | No | `0` | Pixel padding on each side within the target size |
| `--fit contain\|cover` | No | `contain` | `contain` letterboxes; `cover` fills and clips |

PEP 723 dependencies: `resvg-py==0.2.6`, `Pillow==11.3.0`

---

### icon-set.py

Generates the full Tauri desktop icon set from one source SVG. One invocation → 9 files.

```bash
uv run .cursor/skills/image-assets/scripts/icon-set.py \
  src-tauri/icons/graftmark.svg \
  --output-dir src-tauri/icons/ \
  --fill "#1a1a2e" \
  --background transparent
```

**Output files** (written to `--output-dir`):

| File | Size | Purpose |
|------|------|---------|
| `icon.png` | 1024×1024 | Tauri master; required by `generate_context!()` |
| `32x32.png` | 32×32 | Tauri window icon (small) |
| `128x128.png` | 128×128 | Tauri window icon |
| `128x128@2x.png` | 256×256 | Tauri HiDPI window icon |
| `tray-synced.png` | 32×32 | System tray: synced state |
| `tray-drifted.png` | 32×32 | System tray: drifted state |
| `tray-error.png` | 32×32 | System tray: error state |
| `icon.ico` | 16,24,32,48,64,256px embedded | Windows app icon |
| `icon.icns` | 16–1024px multi-size | macOS bundle icon |

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `input_svg` | Yes | — | Source SVG file (positional) |
| `--output-dir <path>` | Yes | — | Directory to write all output files |
| `--fill <color>` | No | `#000000` | Primary icon fill color |
| `--background <color>` | No | `transparent` | Background for all raster outputs |
| `--fit contain\|cover` | No | `contain` | Aspect ratio handling |
| `--tray-fill-synced <color>` | No | `#22c55e` | Synced state tray icon fill |
| `--tray-fill-drifted <color>` | No | `#f59e0b` | Drifted state tray icon fill |
| `--tray-fill-error <color>` | No | `#ef4444` | Error state tray icon fill |
| `--tray-background <color>` | No | `transparent` | Tray icon background |
| `--check` | No | — | CI mode: hash-compare generated vs committed; exits 1 if stale |

PEP 723 dependencies: `resvg-py==0.2.6`, `Pillow==11.3.0`, `icnsutil==1.1.0`

> **`png-to-ico.py` does not exist.** ICO generation is handled by `icon-set.py` (Tauri app icons) and `img-convert.py --format ico` (single-image ICO). `img-upscale.py` handles the raster-to-large use case; it does not replace `svg-to-png.py --size` when an SVG source exists.

---

### img-convert.py

General-purpose raster conversion, optimization, resize, EXIF strip, and tint. Handles image ops that don't require an SVG source.

```bash
# Lossless PNG optimization
uv run .cursor/skills/image-assets/scripts/img-convert.py icon.png --optimize

# Convert to WebP with explicit lossy acknowledgment
uv run .cursor/skills/image-assets/scripts/img-convert.py \
  banner.png --format webp --quality 85 --output banner.webp --allow-lossy
```

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `input` | Yes | — | Source image file (positional) |
| `--output <path>` | No | `<input>.<format>` | Output path |
| `--format png\|jpg\|webp\|avif\|ico` | No | same as input | Target format |
| `--quality <0-100>` | No | `85` | Lossy encoding quality. Requires `--allow-lossy` |
| `--width <px>` | No | — | Resize to width. Requires `--allow-lossy` |
| `--height <px>` | No | — | Resize to height. Requires `--allow-lossy` |
| `--optimize` | No | false | Lossless PNG optimization (PNG output only) |
| `--strip-exif` | No | false | Strip all EXIF metadata (JPEG/WebP) |
| `--tint <color>` | No | — | Apply color tint via grayscale colorize |
| `--allow-lossy` | No | false | Required for JPG/WebP/AVIF output, `--quality`, or resize |
| `--max-size <px>` | No | `8192` | Reject inputs exceeding this pixel dimension |

PEP 723 dependencies: `Pillow==11.3.0`, `pyoxipng==9.1.1`, `piexif==1.1.3`

---

### img-upscale.py

Upscales a raster PNG to a target resolution. Two modes: `vectorize` traces the PNG to SVG then renders at target size (best for flat/icon art, produces mathematically clean output at any scale); `ai` uses Real-ESRGAN NCNN super-resolution (for complex rasters that do not trace cleanly).

```bash
# Flat icon / logo — vectorize path (recommended for geometric art)
uv run .cursor/skills/image-assets/scripts/img-upscale.py \
  icon-256.png output/icon-4000.png --size 4000x4000

# Complex photo-based image — AI super-resolution path
uv run .cursor/skills/image-assets/scripts/img-upscale.py \
  photo-512.png output/photo-2048.png --size 2048x2048 --mode ai
```

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| `input` | Yes | — | Source PNG file (positional) |
| `output` | Yes | — | Output PNG file path (positional) |
| `--size <WxH>` | No | `1024x1024` | Target pixel dimensions |
| `--mode vectorize\|ai` | No | `vectorize` | Upscale strategy |

PEP 723 dependencies: `vtracer`, `resvg-py==0.2.6`, `Pillow==11.3.0`

> **AI mode requires separate install:** `uv pip install realesrgan-ncnn-py` before using `--mode ai`. The script exits with a clear error if the package is absent.

## Security

**SVG defanging before processing untrusted input.** An SVG is an XML document that can carry `<script>` elements, `onload` event handlers, and XXE entity declarations. Strip these before rendering:

```python
import re

def defang_svg(svg_text: str) -> str:
    svg_text = re.sub(r"<script[\s\S]*?</script>", "", svg_text, flags=re.IGNORECASE)
    svg_text = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', "", svg_text)
    svg_text = re.sub(r"<!ENTITY[^>]*>", "", svg_text)
    return svg_text
```

Applies to SVG from user-supplied paths or network sources. Repo SVGs are already trusted.

**No shell invocation for image operations.** Never use `os.system()`, `subprocess.run(shell=True)`, or `subprocess.Popen` for image processing. Shell injection via crafted filenames is a real vector. All operations go through the Python libraries above.

**Memory guardrail for batch scripts.** Large images loaded into PIL can exhaust memory. Enforce before opening:

```python
MAX_IMAGE_SIZE = 8192

with Image.open(path) as probe:
    w, h = probe.size
    if w > MAX_IMAGE_SIZE or h > MAX_IMAGE_SIZE:
        raise ValueError(f"Image too large: {w}x{h}")
```

`img-convert.py` enforces this via `--max-size` (default 8192). Apply the same guard in any new batch script.

## Anti-Patterns

**Never use AI image generation for logo variants.** Logo identity requires exact geometry — only the source SVG guarantees that. All color variants, size variants, and format conversions must derive from the canonical SVG via script.

**Never hardcode fill colors in scripts.** Color is a parameter. Scripts accept `--fill`. Batch variants = loop over the invocation, not forked scripts per color.

**Never resize by post-hoc cropping.** Pass target dimensions to the renderer. Cropping after rendering produces blurry or clipped output because the SVG's logical coordinate space was not mapped to the target canvas.

**Never commit derived assets without a reproducible source pointer.** Every output PNG or ICO must trace to a source SVG and the invocation that produced it — a `Makefile` target, a `scripts/build-icons.sh`, or a comment in `Cargo.toml`. The pipeline must be reproducible from the SVG alone.

**Never omit `--allow-lossy` for format-converting scripts.** Conversion to JPG, WebP, or AVIF discards pixel data irreversibly. `img-convert.py` enforces an explicit `--allow-lossy` flag for these formats, for `--quality`, and for resize. Do not work around it — the flag exists to make the quality trade-off visible and intentional.

**Never import `pyoxipng` as `pyoxipng`.** The PyPI package name is `pyoxipng`; the Python module name is `oxipng`. Use `import oxipng` in scripts, `pyoxipng==x.y.z` in PEP 723 `dependencies`. Confusing the two produces silent `ModuleNotFoundError` at runtime.

**Never use AI image generation to reproduce or enlarge an existing raster.** The model has no memory of the original. Output will be vibe-compatible — similar style, different geometry, proportions, and stroke weights. The correct enlargement path is `img-upscale.py --mode vectorize` (flat design) or `--mode ai` (complex rasters).

**Never upscale a PNG with LANCZOS beyond 2x.** At 3x and above, edges blur and fine lines develop haloing artifacts. Use `img-upscale.py` instead.

## Cross-References

- [diagramming](../diagramming/SKILL.md) — Mermaid diagram generation; no raster asset handling
- [tauri-development](../tauri-development/SKILL.md) — Tauri icon configuration and `generate_context!()` compile-time requirements (`icon.png` must exist at `src-tauri/icons/icon.png`)
- [rust-development](../rust-development/SKILL.md) — Cargo workspace context where icon outputs land
- [image-generation](../image-generation/SKILL.md) — AI image generation decisions, prompt templates, and the "never regenerate to reproduce" boundary

</ANCHORSKILL-IMAGE-ASSETS>
