# Reference: Tech Stack

Technology stack architecture and patterns.

---

## Pattern

### SvelteKit Architecture

Modern SvelteKit projects follow this standard structure:

```
src/frontend/
├── src/
│   ├── lib/
│   │   ├── components/     # Reusable components
│   │   ├── stores/         # State management
│   │   ├── api/            # HTTP client
│   │   └── config/         # Settings and tokens
│   ├── routes/             # SvelteKit routes
│   └── app.css             # Token fallbacks
```

### Settings Flow

Token-based theming follows this flow:

```
Settings JSON (source)
  ↓
Settings Store (runtime state)
  ↓
CSS Variable Sync (CSS custom properties)
  ↓
Components (consume via Tailwind or var(--token))
```

### Environment Configuration

Use Vite environment variables for API endpoints:

**Development:**
```bash
VITE_API_URL=http://localhost:8000
```

**Production:**
```bash
VITE_API_URL=https://api.example.com
```

**Usage in code:**
```typescript
const API_URL = import.meta.env.VITE_API_URL;

export async function fetchData() {
  const response = await fetch(`${API_URL}/api/resource`);
  return response.json();
}
```

### Deployment Pattern

Standard Docker Compose architecture:

```yaml
services:
  frontend:
    build: ./src/frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://backend:8000
  
  backend:
    build: ./src/backend
    ports:
      - "8000:8000"
  
  nginx:
    image: nginx
    ports:
      - "80:80"
    # Proxy / to frontend:3000
    # Proxy /api/* to backend:8000
```

---

## Project Implementation

### Universal-API File Locations

| Component | Path |
|-----------|------|
| Settings JSON | `src/frontend/src/lib/config/default_app_settings.json` |
| Settings Store | `src/frontend/src/lib/stores/settingsStore.ts` |
| CSS Variable Sync | `src/frontend/src/lib/stores/cssVariableSync.ts` |
| Token Fallbacks | `src/frontend/src/app.css` |
| Layout Loading | `src/frontend/src/routes/+layout.svelte` |

### Deployment Specifics

- **Frontend port:** 3000 (production), 4173 (development)
- **Backend port:** 8000
- **SSR adapter:** `@sveltejs/adapter-node`

## Anti-Patterns

```typescript
// ❌ BAD: Using IPC or filesystem from UI
import { invoke } from '@tauri-apps/api';
const result = await invoke('read_file');

// ✅ GOOD: Using HTTP
const response = await fetch(`${API_URL}/api/files`);

// ❌ BAD: Bypassing settings system
const primaryColor = '#3b82f6';

// ✅ GOOD: Using token system
const primaryColor = 'var(--color-primary)';
```

---

## Approved Frontend Packages

| Category | Package | Purpose |
|----------|---------|---------|
| UI Components | `shadcn-svelte` | Svelte 5 component library |
| UI Primitives | `bits-ui@2.x` | Accessible UI primitives |
| Styling | `tailwindcss@4.x` | Utility-first CSS |
| Styling Utils | `tailwind-merge`, `clsx`, `tailwind-variants` | Class composition |
| Forms | `sveltekit-superforms`, `formsnap@2.x` | Form management |
| Validation | `zod@^4` | Schema validation |
| Icons | `@iconify/svelte` | Icon library |

### shadcn-svelte Component Usage

```svelte
<script lang="ts">
import { Button } from '$lib/components/ui/button';
import { Input } from '$lib/components/ui/input';

let value = $state('');
</script>

<Input bind:value placeholder="Enter value..." />
<Button onclick={() => console.log(value)}>Submit</Button>
```

### Form Validation with Zod

```typescript
import { z } from 'zod';

const apiSourceSchema = z.object({
  name: z.string().min(1, "Name is required"),
  url: z.string().url("Must be a valid URL"),
  apiKey: z.string().optional()
});
```

---

## Frontend Package Review Checklist

Before adding new frontend dependencies:

- [ ] Check if existing approved packages can solve the need
- [ ] Verify package is actively maintained (commits within 6 months)
- [ ] Check license compatibility (MIT, Apache 2.0, BSD preferred)
- [ ] Verify package has TypeScript types available
- [ ] Confirm package doesn't duplicate existing functionality
- [ ] Using shadcn-svelte components (not custom reimplementations)
- [ ] Using Tailwind v4 for styling (not inline styles or CSS modules)
- [ ] Using Zod for validation schemas (not custom validators)
- [ ] Using @iconify/svelte for icons (not multiple icon libraries)
- [ ] Components follow Svelte 5 runes syntax
