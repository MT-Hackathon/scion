# Guide: Test Endpoint Pattern

Test endpoint implementation for form validation.

---

## Pattern

### Test Endpoint UI States

| State | Display |
|-------|---------|
| Idle | "Test Endpoint" button |
| Loading | Spinner + "Testing..." |
| Success | Green check + "Connected" |
| Error | Red X + specific error message |

### Implementation

```svelte
<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  
  let testState = $state<'idle' | 'loading' | 'success' | 'error'>('idle');
  let testError = $state<string | null>(null);
  
  async function testEndpoint() {
    if (testState === 'loading') return;
    
    testState = 'loading';
    testError = null;
    
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      
      const response = await fetch(endpointUrl, {
        signal: controller.signal,
        headers: { 'Authorization': `Bearer ${apiKey}` }
      });
      
      clearTimeout(timeout);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      testState = 'success';
      
      // Reset to idle after 3 seconds
      setTimeout(() => { testState = 'idle'; }, 3000);
    } catch (err) {
      testState = 'error';
      testError = err.name === 'AbortError' 
        ? 'Request timed out after 10 seconds'
        : err.message;
    }
  }
</script>

<!-- Template {:else} is rendering control flow, not logic branching — it represents visual state,
     distinct from the "zero else in logic functions" rule that applies to TypeScript/Python code. -->
<div class="test-endpoint">
  <Button 
    onclick={testEndpoint}
    disabled={testState === 'loading'}
    variant={testState === 'success' ? 'success' : testState === 'error' ? 'destructive' : 'default'}
  >
    {#if testState === 'loading'}
      <span class="spinner" /> Testing...
    {:else if testState === 'success'}
      ✓ Connected
    {:else if testState === 'error'}
      ✗ Failed
    {:else}
      Test Endpoint
    {/if}
  </Button>
  
  {#if testError}
    <p class="text-error text-sm mt-2">{testError}</p>
  {/if}
</div>
```

### Requirements

- **Timeout:** 10 seconds maximum
- **Credentials:** Redacted in preview (show only success/failure)
- **Position:** Below URL field
- **Error messages:** Specific and actionable

### Credential Masking

```typescript
function logTestResult(url: string, apiKey: string, success: boolean) {
  // ❌ BAD: Full credential
  console.log(`Tested ${url} with key ${apiKey}`);
  
  // ✅ GOOD: Masked credential
  const masked = apiKey.substring(0, 4) + '***';
  console.log(`Tested ${url} with key ${masked}: ${success ? 'OK' : 'FAILED'}`);
}
```

---

## Project Implementation

### Location

Test endpoint functionality is typically implemented in form components:
- `src/frontend/src/lib/components/forms/ApiSourceFormEnhanced.svelte`

### Backend Test Endpoint

For secure credential testing, use a backend endpoint:

```typescript
// Don't test credentials directly from UI
// Instead, send to backend for testing
async function testCredentials(config: ApiConfig) {
  const response = await fetch(`${API_URL}/api/connections/test`, {
    method: 'POST',
    body: JSON.stringify({
      url: config.url,
      auth_type: config.auth_type,
      credential_ref: config.credential_ref // Reference, not actual credential
    })
  });
  
  const result = await response.json();
  return result.success;
}
```
