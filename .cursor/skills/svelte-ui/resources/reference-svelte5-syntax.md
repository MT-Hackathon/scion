# Reference: Svelte 5 Syntax

Complete Svelte 4 to Svelte 5 migration reference.

---

## Pattern

### Syntax Migration Table

| Svelte 4 (NEVER) | Svelte 5 (ALWAYS) |
| ---------------- | ----------------- |
| `export let prop` | `let { prop } = $props()` |
| `$: derived = value` | `let derived = $derived(value)` |
| `$: { sideEffect() }` | `$effect(() => { sideEffect() })` |
| `let count = 0` (reactive) | `let count = $state(0)` |
| `<slot />` | `{@render children?.()}` with `Snippet` |
| `on:click={handler}` | `onclick={handler}` |
| `createEventDispatcher` | expose callback props |
| `$$Props` / `$$restProps` | typed `$props()` destructuring |

### Component Structure

Standard Svelte 5 component structure:

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  
  // Props
  let { 
    value = $bindable(),
    onchange,
    children
  }: {
    value?: string;
    onchange?: (value: string) => void;
    children?: Snippet;
  } = $props();
  
  // State
  let localState = $state(false);
  
  // Derived
  let computed = $derived(value.toUpperCase());
  
  // Effects
  $effect(() => {
    console.log('Value changed:', value);
  });
</script>

<div>
  {#if children}
    {@render children()}
  {/if}
</div>

<style>
  /* Only for unique cases, never colors */
</style>
```

### Props Pattern

```svelte
<script lang="ts">
  // Simple props
  let { name, age } = $props();
  
  // With defaults
  let { name = 'Anonymous', age = 0 } = $props();
  
  // Bindable props
  let { value = $bindable() } = $props();
  
  // With types
  let { 
    name,
    age 
  }: { 
    name: string; 
    age: number; 
  } = $props();
</script>
```

### State Pattern

```svelte
<script lang="ts">
  // Primitive state
  let count = $state(0);
  
  // Object state
  let user = $state({ name: '', email: '' });
  
  // Array state
  let items = $state<string[]>([]);
  
  // Update state
  count++;
  user.name = 'John';
  items.push('new item');
</script>
```

### Derived Pattern

```svelte
<script lang="ts">
  let count = $state(0);
  
  // Simple derived
  let doubled = $derived(count * 2);
  
  // Complex derived
  let summary = $derived.by(() => {
    if (count === 0) return 'Zero';
    if (count < 10) return 'Small';
    return 'Large';
  });
</script>
```

### Effect Pattern

```svelte
<script lang="ts">
  let count = $state(0);
  
  // Side effect on change
  $effect(() => {
    console.log('Count is now:', count);
  });
  
  // Effect with cleanup
  $effect(() => {
    const interval = setInterval(() => count++, 1000);
    return () => clearInterval(interval);
  });
</script>
```

### Event Handler Pattern

```svelte
<!-- Svelte 5: Direct handlers -->
<button onclick={handleClick}>Click</button>
<input oninput={(e) => value = e.target.value} />
<div onmouseover={handleHover} onmouseleave={handleLeave}>
  Hover me
</div>
```

### Snippet Pattern

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  
  let { header, children }: {
    header?: Snippet;
    children?: Snippet;
  } = $props();
</script>

<div class="card">
  {#if header}
    <div class="header">
      {@render header()}
    </div>
  {/if}
  
  <div class="content">
    {@render children?.()}
  </div>
</div>
```
