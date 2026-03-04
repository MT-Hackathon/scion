# Theme Service Implementation

The `ThemeService` manages the application's visual theme (light vs. dark) using Angular Signals and persists the user's preference.

See the complete, annotated implementation in [`../blueprints/theme.service.ts`](../blueprints/theme.service.ts).

## Key Mechanisms

### Signal Encapsulation
Theme state lives in a private `_isDarkMode` signal exposed as a readonly signal. Only `ThemeService` can mutate it — single source of truth.

### Preference Fallback Chain
`stored preference ?? system preference (matchMedia) ?? false` — authoritative wins; safe default is light mode.

### Overlay Container Synchronization
Material components (dialogs, menus) render in a separate overlay container outside the app root. `ThemeService` toggles theme classes on that container explicitly, or overlays render without the active theme.

### Window API Isolation
All `window.matchMedia` and `localStorage` calls are wrapped in `try/catch`. This prevents crashes in SSR and headless test environments where these APIs throw or are absent.
