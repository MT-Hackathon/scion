# Material 3 Palette Reference

This project uses Material 3 color palettes generated via the Angular Material CLI.

## Palette Structure

Each palette file (e.g., `_prism-colors-blue.scss`) defines:

- **Primary**: Main brand color.
- **Secondary**: Supporting UI color roles.
- **Tertiary**: Accent roles for contrast.
- **Neutral**: Zinc-based neutral range for surfaces/backgrounds (avoid blue-tinted slate neutrals).
- **Error**: Validation and error state colors.

Palettes are represented as Sass maps with tonal values from 0 to 100.

## Generation

Generate palettes with:

```bash
ng generate @angular/material:theme-color
```

This command creates Sass maps and mixins used by `mat.theme()`.

## Theme Variants

Variant palettes are applied in `src/style.scss` through `mat.theme()` and class-based selectors.

## High Contrast Support

Palette files may include `high-contrast-overrides` mixins using `_high-contrast-value` helpers to improve accessible contrast in light and dark contexts.
