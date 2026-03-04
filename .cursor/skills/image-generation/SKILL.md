---
name: image-generation
description: "Governs AI image generation decisions, prompt structure, and asset sourcing strategy. Use when using GenerateImage, creating icons, illustrations, marketing banners, or sourcing any image asset from scratch. DO NOT use for programmatic derivation of existing SVG assets (see image-assets) or Mermaid diagrams (see diagramming)."
---

<ANCHORSKILL-IMAGE-GENERATION>

# Image Generation

Governance for when to generate, how to prompt, and what to do with output. GenerateImage is the last resort — not the first tool.

## Table of Contents

- [Decision Framework](#decision-framework)
- [Prompt Engineering Principles](#prompt-engineering-principles)
- [Prompt Templates](#prompt-templates)
- [Anti-Patterns](#anti-patterns)
- [Post-Generation Pipeline](#post-generation-pipeline)
- [Resources](#resources)
- [Cross-References](#cross-references)

## Decision Framework

Evaluate these paths in order. Stop at the first viable option — generation costs tokens, time, and produces non-reproducible output.

**1. Derive from SVG** — If a canonical SVG exists for this asset, use `image-assets` scripts (`svg-to-png.py`, `icon-set.py`). SVG is resolution-independent: any size, any color, any format from one source. Always check for an SVG first.

**2. Upscale or vectorize an existing raster** — If a PNG exists, use `img-upscale.py` (`--mode vectorize` for flat/icon art, `--mode ai` for complex rasters). AI generation cannot reproduce an existing asset. Output will be vibe-compatible — same mood, completely different geometry, proportions, and stroke weights. `img-upscale.py` preserves what you have.

**3. Source from an OSS icon library** — Heroicons, Phosphor, Lucide, and Tabler cover the vast majority of UI icon needs. Scalable, consistent, free, zero generation cost. Check these before generating.

**4. Generate a new concept** — Only when no existing asset or library provides a viable starting point. Proceed to Prompt Templates.

## Prompt Engineering Principles

These structural properties predict generation quality across models.

**Front-load the subject.** The opening phrase carries disproportionate weight. Lead with the single most important thing the image must be.

**Constraint density beats description length.** Explicit exclusions ("no text", "no gradients", "no drop shadows") prevent failure modes more reliably than describing what you want. A tight negative list is more valuable than an elaborate positive description.

**Style anchor before subject detail.** Establish the visual language first ("flat vector icon, geometric, two-color"), then add subject specifics. Style + constraints transfer across models; detailed subject descriptions do not.

**One concept per generation.** Complex multi-element compositions fail more often than simple ones. Decompose into separate calls; composite in post if needed.

**Reference the asset type in the first phrase.** "App icon:" or "Flat vector illustration:" primes the model's output toward the correct canvas constraints before any content description.

## Prompt Templates

Abbreviated templates by asset type. Full versions with failure-mode commentary are in [`resources/reference-prompt-templates.md`](resources/reference-prompt-templates.md).

**App icon / tray icon**
```
Flat vector app icon, geometric, [1-2 word subject].
No text. No gradients. No drop shadows. No photographic textures.
[Transparent | solid white] background.
High-contrast silhouette, legible at 16px.
```

**Illustration / hero graphic**
```
[Style anchor: flat vector illustration | isometric line art | ...], [subject description].
No text. No realistic textures. No photographs.
[Aspect ratio]. [Mood/palette anchors].
```

**App Store / marketing banner**
```
[Style anchor], [action-oriented subject with clear focal point].
No text overlay. 1200×630 composition.
Dominant colors: [2-3 hex or named colors].
```

**Abstract texture / background**
```
[Pattern type] texture, [density], [color range].
No brand marks. No organic photographic textures. No faces.
Seamlessly tileable.
```

## Anti-Patterns

**Never use GenerateImage to reproduce or upscale an existing asset.** The model has no memory of the original. Output is vibe-compatible — same mood, completely different geometry, proportions, and stroke weights. Use `img-upscale.py` instead.

**Never generate logo variants from a prompt.** Logo identity is exact geometry. Variants must derive from the canonical SVG via `svg-to-png.py` or `icon-set.py`. Prompt-based "same logo, different color" produces a different logo.

**Never expect reliable text rendering.** All current generation models fail unpredictably at text. If text is needed, generate without it and composite real typography in post.

**Never expect exact color matching.** Generated output approximates palette. Run `img-convert.py --tint` post-generation for color correction when fidelity matters.

**Never commit generated output without documenting the prompt.** Generated assets are not reproducible without the originating prompt. Record it as a sidecar `.txt` file alongside the asset, as a comment in the build script, or in EXIF metadata via `img-convert.py`. Undocumented generated assets are orphans — the next session cannot reproduce or iterate on them.

## Post-Generation Pipeline

After `GenerateImage` produces output:

1. Run `img-convert.py` — optimize, resize to target dimensions, convert format
2. Strip EXIF before publishing: `img-convert.py --strip-exif`
3. If the output needs to become an icon variant, run `vtracer` directly to produce an SVG source file, then use `icon-set.py` or `svg-to-png.py` to generate the needed sizes
4. Document the originating prompt alongside the committed asset

## Resources

- **reference-prompt-templates.md** — full prompt templates for each asset type with failure-mode commentary; use when building prompts for non-trivial generation tasks

## Cross-References

- [image-assets](../image-assets/SKILL.md) — programmatic derivation, upscaling, format conversion, icon set generation; the correct path for all existing-asset work
- [diagramming](../diagramming/SKILL.md) — Mermaid diagram generation; not for raster image assets

</ANCHORSKILL-IMAGE-GENERATION>
