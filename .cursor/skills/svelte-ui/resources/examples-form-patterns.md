# Examples: Form Patterns

Form store patterns and input integration.

---

## Pattern

### Form Store Pattern

Config forms should use a central store factory with this API:
- `state` - Svelte store containing form values
- `errors` - Svelte store containing validation errors
- `updateField(path, value)` - Update a single field
- `validate()` - Run validation, returns boolean
- `reset()` - Reset to initial values

### Basic Usage

```svelte
<script lang="ts">
  import { get } from 'svelte/store';
  import { Input } from '$lib/components/ui/input';
  import { Button } from '$lib/components/ui/button';
  
  let { initialConfig, onsave } = $props();
  
  const form = createFormStore(initialConfig);
  const state = form.state;
  const errors = form.errors;
  
  async function handleSave() {
    if (!form.validate()) {
      // Note: $errors works in templates but use get() in functions
      console.error('Validation failed:', get(errors));
      return;
    }
    onsave?.(get(state));
  }
</script>

<div class="form-container">
  <Input 
    type="text"
    bind:value={$state.base_url} 
    placeholder="Base URL"
  />
  {#if $errors.base_url}
    <p class="error">{$errors.base_url}</p>
  {/if}
  
  <Button onclick={handleSave}>Save</Button>
</div>
```

### Nested Components

Pass `values`, `errors`, and `onchange` to nested components:

**Parent:**
```svelte
<DynamicAuthFields 
  values={$state}
  errors={$errors}
  onchange={(field, value) => form.updateField(field, value)}
/>
```

**Child:**
```svelte
<script lang="ts">
  let { values, errors, onchange } = $props();
</script>

{#if values.auth_type === 'oauth2'}
  <Input 
    type="text"
    value={values.oauth_client_id}
    oninput={(e) => onchange('oauth_client_id', e.target.value)}
  />
{/if}
```

### Input Component Patterns

**Text Input:**
```svelte
<Input type="text" bind:value={$state.field} placeholder="Enter value" />
```

**Password Input:**
```svelte
<Input type="password" bind:value={$state.password} placeholder="Enter password" />
```

**Number Input:**
```svelte
<Input type="number" bind:value={$state.count} min="0" max="100" />
```

### Best Practices

**Correct:**
```svelte
<Input bind:value={$store.resource.field} />
const form = createFormStore(initial);
<Input bind:value={$form.state.field} />
```

**Incorrect:**
```svelte
let localValue = $state('');  // WRONG - local state
<Input bind:value={localValue} />

<input type="text" bind:value={field} />  // WRONG - plain input
```

---

## Project Implementation

### Form Store Location

Location: `src/frontend/src/lib/stores/configFormStores.ts`

Available factories:
- `createApiSourceFormStore(config)`
- `createTransformFormStore(config)`

### Complete Form Example

```svelte
<script lang="ts">
  import { get } from 'svelte/store';
  import { Input } from '$lib/components/ui/input';
  import { Button } from '$lib/components/ui/button';
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '$lib/components/ui/select';
  import { createApiSourceFormStore } from '$lib/stores/configFormStores';
  
  let { initialConfig, onsave } = $props();
  
  const form = createApiSourceFormStore(initialConfig);
  const state = form.state;
  const errors = form.errors;
  
  let isLoading = $state(false);
  
  async function handleSave() {
    if (isLoading) return;
    if (!form.validate()) return;
    
    isLoading = true;
    try {
      await onsave(get(state));
    } catch (err) {
      console.error('Save failed:', err);
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="space-y-4">
  <div>
    <label for="name">Name</label>
    <Input 
      id="name"
      type="text"
      bind:value={$state.name}
      placeholder="Configuration name"
      disabled={isLoading}
    />
    {#if $errors.name}
      <p class="text-error text-sm">{$errors.name}</p>
    {/if}
  </div>
  
  <div>
    <label for="auth-type">Auth Type</label>
    <Select bind:value={$state.authconfig_auth_type}>
      <SelectTrigger id="auth-type">
        <SelectValue placeholder="Select auth type" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="api_key">API Key</SelectItem>
        <SelectItem value="oauth2">OAuth2</SelectItem>
        <SelectItem value="basic">Basic Auth</SelectItem>
      </SelectContent>
    </Select>
  </div>
  
  <Button onclick={handleSave} disabled={isLoading}>
    {isLoading ? 'Saving...' : 'Save Configuration'}
  </Button>
</div>
```

### Styling Tokens

Form elements use these shared classes:
- `.node-select-trigger` - Select trigger styling
- `.node-select-content` - Select dropdown styling
- `.node-select-item` - Select item styling
- `.node-text-input` - Text input styling

All inherit from `--active-node-color` set by parent wrapper.
