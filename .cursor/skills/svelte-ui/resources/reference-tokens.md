# Reference: Design Token System

CSS variable definitions and palette architecture.

---

## Pattern

### Token Architecture

Token-based theming flows from configuration to components:

```
Settings JSON (source)
  ↓ (loaded by settings store)
Settings Store (runtime state)
  ↓ (synced by CSS variable sync)
CSS Custom Properties (--token-name)
  ↓ (consumed by)
Components (Tailwind or var(--token))
```

### Standard Token Categories

**Text:**
- `--text-primary` - Primary text color
- `--text-secondary` - Secondary text color
- `--text-muted` - Muted text color
- `--text-error` - Error message text

**Background:**
- `--bg-primary` - Primary background
- `--bg-secondary` - Secondary background
- `--bg-tertiary` - Tertiary background
- `--bg-hover` - Hover state background
- `--bg-active` - Active state background

**Border:**
- `--border-default` - Default border color
- `--border-subtle` - Subtle border color
- `--border-strong` - Strong border color

**Accent:**
- `--accent-primary` - Primary accent color
- `--accent-secondary` - Secondary accent color
- `--accent-success` - Success state
- `--accent-warning` - Warning state
- `--accent-error` - Error state

**Spacing:**
- `--spacing-xs` through `--spacing-xl`

**Typography:**
- `--font-size-xs` through `--font-size-2xl`
- `--font-weight-normal` through `--font-weight-bold`

**Elevation:**
- `--shadow-sm` through `--shadow-xl`

### Theme Switching

Tokens have different values per theme. Theme toggle changes `data-theme` attribute on `:root`; CSS variables update automatically.

```css
:root[data-theme="light"] {
  --text-primary: #1a1a1a;
  --bg-primary: #ffffff;
}

:root[data-theme="dark"] {
  --text-primary: #f5f5f5;
  --bg-primary: #0a0a0a;
}
```

### Token Usage in Components

**Via Tailwind:**
```svelte
<div class="bg-primary text-primary border-default">
  Content
</div>
```

**Direct token access:**
```svelte
<div style="
  color: var(--text-primary);
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
">
  Content
</div>
```

### When to Use Tailwind vs Direct Tokens

**Tailwind classes** for standard cases:
- Automatically use token values
- Consistent spacing/sizing
- Better dev experience

**Direct CSS variables** for special cases:
- Gradients
- Complex calculations
- Dynamic values
- Canvas node styling

---

## Project Implementation

### Universal-API Token Files

| File | Purpose |
|------|---------|
| `src/frontend/src/lib/config/default_app_settings.json` | Source of truth for all tokens |
| `src/frontend/src/lib/types/settings.ts` | TypeScript definitions |
| `src/frontend/src/lib/stores/cssVariableSync.ts` | Syncs settings to CSS |
| `src/frontend/src/app.css` | Build-time fallbacks |

### Settings JSON Structure

```json
{
  "theme": "light",
  "palette": {
    "light": {
      "text": { "primary": "#1a1a1a", "secondary": "#6b7280" },
      "background": { "primary": "#ffffff", "secondary": "#f9fafb" }
    },
    "dark": {
      "text": { "primary": "#f5f5f5", "secondary": "#9ca3af" },
      "background": { "primary": "#0a0a0a", "secondary": "#1f2937" }
    }
  },
  "canvas": {
    "leftToolbarWidth": { "lg": 280, "md": 240, "sm": 200 }
  }
}
```

### Adding New Tokens

1. Add to `default_app_settings.json`
2. Update TypeScript types in `settings.ts`
3. Ensure `cssVariableSync.ts` emits the new CSS variable
4. Use in components via `var(--new-token)` or Tailwind
