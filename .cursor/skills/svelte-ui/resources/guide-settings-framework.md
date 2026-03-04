# Guide: Settings Framework

Settings store flow and configuration system.

---

## Pattern

### Architecture

Token-based theming uses a layered architecture:

1. **Source of Truth** - JSON configuration file with all visual tokens
2. **Runtime Store** - Svelte store for runtime access and mutations
3. **CSS Sync** - Reactive system that syncs settings to CSS custom properties
4. **Components** - Consume via `var(--token)` or Tailwind

### Settings Store API

```typescript
import { settingsStore, settingsActions } from '$lib/stores/settingsStore';
import { get } from 'svelte/store';

// Read settings
const settings = get(settingsStore);

// Update setting
settingsActions.updateCanvasSetting('leftToolbarWidth.lg', 280);

// Update theme
settingsActions.updateTheme('dark');

// Reset to defaults
settingsActions.resetToDefaults();
```

### Subscribing to Settings

```svelte
<script lang="ts">
  import { settingsStore } from '$lib/stores/settingsStore';
</script>

<div>
  Current theme: {$settingsStore.theme}
</div>
```

### Updating Settings

```svelte
<script lang="ts">
  import { settingsStore, settingsActions } from '$lib/stores/settingsStore';
  
  function toggleTheme() {
    const newTheme = $settingsStore.theme === 'light' ? 'dark' : 'light';
    settingsActions.updateTheme(newTheme);
  }
</script>

<button onclick={toggleTheme}>Toggle Theme</button>
```

### CSS Variable Sync

The sync system automatically updates CSS custom properties when settings change:

1. Settings store changes
2. Reactive sync statement triggers
3. Updates `:root` CSS variables
4. Components using `var(--token)` update automatically

### Responsive Layout Values

Layout dimensions use `{lg, md, sm}` objects:

**In settings:**
```json
{
  "leftToolbarWidth": {
    "lg": 280,
    "md": 240,
    "sm": 200
  }
}
```

**Synced to CSS:**
```css
:root {
  --left-toolbar-width-lg: 280px;
  --left-toolbar-width-md: 240px;
  --left-toolbar-width-sm: 200px;
}
```

**Used in components:**
```svelte
<div style="width: var(--left-toolbar-width-lg)">
  Toolbar content
</div>
```

**Responsive media queries:**
```css
.toolbar {
  width: var(--left-toolbar-width-lg);
}

@media (max-width: 1024px) {
  .toolbar {
    width: var(--left-toolbar-width-md);
  }
}

@media (max-width: 768px) {
  .toolbar {
    width: var(--left-toolbar-width-sm);
  }
}
```

### Layout Config Pattern

Derive CSS variables from settings instead of exporting hardcoded constants:

**Old pattern (PROHIBITED):**
```typescript
export const LEFT_TOOLBAR_WIDTH = 280;
```

**New pattern (REQUIRED):**
```typescript
export function getLeftToolbarWidth(size: 'lg' | 'md' | 'sm'): number {
  return get(settingsStore).canvas.leftToolbarWidth[size];
}
```

Components should use CSS variables directly instead of importing constants.

---

## Project Implementation

### Universal-API File Locations

| Purpose | Path |
|---------|------|
| Settings JSON | `src/frontend/src/lib/config/default_app_settings.json` |
| Settings Store | `src/frontend/src/lib/stores/settingsStore.ts` |
| CSS Variable Sync | `src/frontend/src/lib/stores/cssVariableSync.ts` |
| TypeScript Types | `src/frontend/src/lib/types/settings.ts` |
| Layout Config | `src/frontend/src/lib/config/layoutConfig.ts` |

### TypeScript Types

Types must match JSON structure:

```typescript
export interface AppSettings {
  theme: 'light' | 'dark';
  palette: {
    light: ColorPalette;
    dark: ColorPalette;
  };
  canvas: CanvasSettings;
}

export interface ColorPalette {
  text: { primary: string; secondary: string; };
  background: { primary: string; secondary: string; };
}

export interface CanvasSettings {
  leftToolbarWidth: ResponsiveValue;
  rightSidebarWidth: ResponsiveValue;
}

export interface ResponsiveValue {
  lg: number;
  md: number;
  sm: number;
}
```

### Adding New Tokens

1. Add to `default_app_settings.json`
2. Update TypeScript types in `settings.ts`
3. Ensure `cssVariableSync.ts` emits the new CSS variable
4. Use in components via `var(--new-token)` or Tailwind
