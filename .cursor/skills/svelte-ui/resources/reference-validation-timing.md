# Reference: Validation Timing

When and how to validate form inputs.

---

## Pattern

### Validation Events

| Event | Timing | Action |
|-------|--------|--------|
| Blur | Immediate | Validate single field |
| Change | Debounce 300ms | Validate single field |
| Submit | Immediate | Full schema validation |

### Error Display

- **Inline errors:** Red text + icon below field
- **Error summary:** At form top
- **Focus first error** on submit

### Error Message Quality

| Status | Example |
|--------|---------|
| Good | "URL must start with http:// or https://" |
| Good | "Missing API key. Add to connection manager." |
| Bad | "URL is invalid" (not actionable) |

### Zod Integration

```typescript
import { z } from 'zod';

const schema = z.object({
  url: z.string().url().startsWith('http'),
  apiKey: z.string().min(1, 'API key required'),
});

// Safe parse for user input
const result = schema.safeParse(formData);
if (!result.success) {
  result.error.issues.forEach(issue => {
    setFieldError(issue.path[0], issue.message);
  });
}
```

---

## Project Implementation

### Validation Utils

Location: `src/frontend/src/lib/utils/validation.ts`

Shared validation helpers for common patterns:
- URL validation
- Email validation
- Required field validation
- Pattern matching

### Form Config

Location: `src/frontend/src/lib/config/formConfig.ts`

Shared option sets and field configurations for consistent form structure.

### Field-Level Validation

```svelte
<script lang="ts">
  import { validateUrl } from '$lib/utils/validation';
  
  let url = $state('');
  let error = $state<string | null>(null);
  
  function handleBlur() {
    const result = validateUrl(url);
    error = result.valid ? null : result.message;
  }
</script>

<Input 
  bind:value={url}
  onblur={handleBlur}
/>
{#if error}
  <p class="text-error">{error}</p>
{/if}
```
