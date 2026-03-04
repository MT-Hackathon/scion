# Examples: CSS Patterns

Loading states, custom components, and styling patterns.

---

## Pattern

### Loading State Pattern

Use spinner components for async operations:

**When to use:**
- API calls >200ms
- Canvas operations >50ms
- Data processing operations
- File uploads
- Any user-triggered async operation

**DO NOT use for:**
- Instant operations (<50ms)
- Known-duration tasks (use progress bar instead)
- Background operations (user doesn't need to wait)
- Passive updates (use subtle indicators)

### Basic Loading Pattern

```svelte
<script lang="ts">
  let isLoading = $state(false);
  
  async function handleAction() {
    if (isLoading) return;  // Prevent double-clicks
    
    isLoading = true;
    try {
      await fetch('/api/endpoint');
    } catch (err) {
      console.error('Failed:', err);
    } finally {
      isLoading = false;
    }
  }
</script>

<button onclick={handleAction} disabled={isLoading}>
  {#if isLoading}
    Loading...
  {:else}
    Click me
  {/if}
</button>
```

### Loading with Error Handling

```svelte
<script lang="ts">
  let isLoading = $state(false);
  let error = $state<string | null>(null);
  
  async function handleAction() {
    if (isLoading) return;
    
    isLoading = true;
    error = null;
    
    try {
      const response = await fetch('/api/endpoint');
      if (!response.ok) throw new Error('Request failed');
      const data = await response.json();
      // Handle success
    } catch (err) {
      error = err.message;
    } finally {
      isLoading = false;
    }
  }
</script>

<div>
  <button onclick={handleAction} disabled={isLoading}>
    {isLoading ? 'Loading...' : 'Submit'}
  </button>
  
  {#if error}
    <p class="text-error" role="alert">{error}</p>
  {/if}
</div>
```

### Accessibility for Loading States

Always include accessibility attributes:

```svelte
<div role="status" aria-live="polite">
  {#if isLoading}
    <span class="sr-only">Loading...</span>
  {/if}
</div>
```

### Progress Bar Pattern

For known-duration tasks, use progress bar instead of spinner:

```svelte
<script lang="ts">
  let progress = $state(0);
</script>

<div class="progress-container">
  <div 
    class="progress-bar"
    style="width: {progress}%"
    role="progressbar"
    aria-valuenow={progress}
    aria-valuemin="0"
    aria-valuemax="100"
  />
</div>
```

### Skeleton Loading

For content placeholders:

```svelte
<div class="skeleton-container">
  <div class="skeleton-line" />
  <div class="skeleton-line short" />
  <div class="skeleton-box" />
</div>

<style>
  .skeleton-line {
    height: 1rem;
    background: var(--bg-tertiary);
    border-radius: 0.25rem;
    animation: pulse 2s infinite;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>
```

---

## Project Implementation

### ThinkingAnimation Component

Universal-API uses `ThinkingAnimation.svelte` for loading states:

```svelte
<script lang="ts">
  import ThinkingAnimation from '$lib/components/ThinkingAnimation.svelte';
  
  let isLoading = $state(false);
</script>

<button onclick={handleAction} disabled={isLoading}>
  {#if isLoading}
    <ThinkingAnimation />
  {:else}
    Click me
  {/if}
</button>
```

### Custom Components

Use custom components from `$lib/components/custom/` for:

**Custom Button:**
```svelte
import Button from '$lib/components/custom/Button.svelte';

<Button 
  variant="primary"
  disabled={isLoading}
  onclick={handleClick}
>
  {isLoading ? 'Loading...' : 'Submit'}
</Button>
```

**Custom Input:**
```svelte
import Input from '$lib/components/custom/Input.svelte';

<Input 
  type="text"
  bind:value={name}
  placeholder="Enter name"
/>
```

**Custom Card:**
```svelte
import Card from '$lib/components/custom/Card.svelte';

<Card>
  <h2>Card Title</h2>
  <p>Card content goes here</p>
</Card>
```

### Canvas Loading

For canvas operations, use 50ms threshold:

```svelte
<script lang="ts">
  import ThinkingAnimation from '$lib/components/ThinkingAnimation.svelte';
  
  let isProcessing = $state(false);
</script>

{#if isProcessing}
  <div class="canvas-overlay">
    <ThinkingAnimation />
  </div>
{/if}
```
