# Reference: Prompt Templates by Asset Type

Full prompt templates with failure-mode commentary. Use these when composing non-trivial generation prompts. The abbreviated versions in `SKILL.md` are sufficient for routine cases.

---

## App Icon / Tray Icon

**Failure modes this template prevents:** gradients that disappear at small sizes, text that renders as visual noise, drop shadows that bleed at 16px, photographic textures that obscure the silhouette.

```
Flat vector app icon, geometric, [subject in 1-2 words].
Single stroke weight throughout. 1 to 2 elements maximum.
No text. No gradients. No drop shadows. No photographic textures. No lens flares.
Background: [transparent | solid white | solid #xxxxxx].
High-contrast silhouette. Must read clearly at 16 pixels.
Color: [primary fill color], [optional secondary accent].
```

**When to split the call:**
- If the icon needs both a foreground mark and a distinct background shape, generate them separately and composite. A single prompt for "icon on colored background" frequently merges the two elements into an unclean edge.

---

## System Tray Icon (State Variants)

Tray icons are 16×16 or 32×32px. Legibility is the only success criterion.

```
Minimal flat icon, [subject], suitable for a 32×32 system tray.
No text. No gradients. Solid fill only.
Background: transparent.
Color: [state color — e.g., #22c55e for synced, #ef4444 for error].
Maximum 2 visual elements. Heavy stroke relative to canvas size.
```

**Note:** For state variants (synced / drifted / error) derive from a canonical SVG via `icon-set.py` with `--tray-fill-*` parameters. Only generate an original concept here; color variants belong to `image-assets`.

---

## Illustration / Hero Graphic

**Failure modes this template prevents:** realism bleeding into a flat design set, unintended text appearing in scene, inconsistent style across a multi-illustration set.

```
[Style anchor: flat vector illustration | isometric line art | outlined icon illustration],
[subject description — one clear action or scene].
No text. No realistic textures. No photographs. No stock photo composition.
Aspect ratio: [16:9 | 1:1 | 4:3 | custom].
Mood: [calm and minimal | bold and energetic | ...].
Palette: [2-3 dominant colors, e.g., #1a1a2e navy, #ffffff white, #22c55e green].
Consistent with [flat design | Material Design | ...] visual language.
```

**Style consistency across a set:**
Fix the style anchor and palette across all calls in a set. Do not vary the style phrase — even minor wording changes ("flat illustration" vs "vector flat illustration") shift the model's output distribution enough to break visual coherence.

---

## App Store / Marketing Banner

**Failure modes this template prevents:** text overlay that conflicts with App Store text requirements, off-center composition that crops poorly at different aspect ratios, over-busy scenes that lose the focal point at thumbnail size.

```
[Style anchor], [action-oriented subject with single clear focal point].
No text overlay. No watermarks. No UI chrome.
Composition: subject centered or rule-of-thirds. Safe zone: 1200×630.
Dominant colors: [2-3 colors].
[Optional: white negative space on left/right for text placement in post].
```

**Post-generation:**
All text (app name, tagline, CTA) is added in post using real typography tools. Prompting for text placement inside the image will produce illegible or incorrectly spelled output — do not attempt it.

---

## Abstract Texture / Background Pattern

**Failure modes this template prevents:** organic photographic textures appearing in geometric pattern prompts, brand marks appearing as noise, non-tileable seam artifacts.

```
[Pattern type: geometric grid | dot matrix | topographic lines | hexagonal mesh | ...],
[density: sparse | medium | dense], [color range: light gray tones | ...].
No brand marks. No organic photographic textures. No faces. No text.
Seamlessly tileable. Flat, no depth or shadows.
Style: [minimalist | technical | organic-abstract].
```

**Tileability:** Add "seamlessly tileable" as an explicit constraint, not a hope. For critical applications, verify by placing four copies in a 2×2 grid — seam artifacts are invisible in single-image preview and obvious in layout.

---

## Prompt Engineering Quick Reference

| Principle | Application |
|-----------|-------------|
| Front-load the subject | First phrase: "Flat vector app icon, tree." Not: "I want an icon that shows a tree in a flat vector style." |
| Constraint density > description length | "No text. No gradients. No drop shadows." is more reliable than "clean and minimal." |
| Style anchor before detail | "Isometric line art, server rack" — not "a server rack in isometric line art style." |
| One concept per call | Generate foreground and background separately; composite in post. |
| Document the prompt | Sidecar `.txt` or code comment. Undocumented = irreproducible. |
