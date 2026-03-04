# Examples: HTTP Patterns

HTTP communication patterns and examples.

---

## Pattern

### Response Envelope Pattern

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}

async function fetchResource<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`);
  const result: ApiResponse<T> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error?.message || 'Request failed');
  }
  
  return result.data;
}
```

### Error Handling Pattern

```typescript
async function loadData() {
  let errorBanner = $state<string | null>(null);
  
  try {
    const data = await fetchResource<Pipeline[]>('/api/pipelines');
    // Use data...
  } catch (err) {
    errorBanner = err.message;
    showErrorBanner(errorBanner);
  }
}
```

### Timeout and AbortController Pattern

**Short timeout for initial request:**
```typescript
async function quickFetch<T>(endpoint: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      signal: controller.signal
    });
    clearTimeout(timeout);
    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out after 5 seconds');
    }
    throw err;
  }
}
```

**Long polling with increasing timeout:**
```typescript
async function pollJobStatus(jobId: string): Promise<JobStatus> {
  let timeout = 5000; // Start at 5s
  
  while (true) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    
    try {
      const status = await fetch(`${API_URL}/api/jobs/${jobId}`, {
        signal: controller.signal
      });
      clearTimeout(timer);
      
      const result = await status.json();
      
      if (result.data?.status === 'completed' || result.data?.status === 'failed') {
        return result.data;
      }
      
      // Increase timeout (up to 30s)
      timeout = Math.min(timeout * 1.5, 30000);
      
      await new Promise(r => setTimeout(r, 2000));
    } catch (err) {
      clearTimeout(timer);
      throw err;
    }
  }
}
```

### Type-Safe Response Pattern

```typescript
import { z } from 'zod';

const pipelineSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.enum(['draft', 'active', 'archived'])
});

const pipelineResponseSchema = z.object({
  success: z.literal(true),
  data: z.array(pipelineSchema)
});

async function fetchPipelinesTypeSafe(): Promise<Pipeline[]> {
  const response = await fetch(`${API_URL}/api/pipelines`);
  const json = await response.json();
  
  const result = pipelineResponseSchema.safeParse(json);
  
  if (!result.success) {
    throw new Error('Invalid response format');
  }
  
  return result.data.data;
}
```

### Prohibited Patterns

```typescript
// ❌ BAD: Using custom IPC
window.electron.invoke('fetch_data');

// ✅ GOOD: Using HTTP
await fetch(`${API_URL}/api/data`);

// ❌ BAD: Swallowing errors
try {
  await apiCall('/api/data');
} catch (err) {
  // Silent failure
}

// ✅ GOOD: Surfacing errors
try {
  await apiCall('/api/data');
} catch (err) {
  showErrorToUser(err.message);
}

// ❌ BAD: Window hacks
window.__backend_bridge__.send(data);

// ✅ GOOD: Standard HTTP POST
await fetch(`${API_URL}/api/data`, {
  method: 'POST',
  body: JSON.stringify(data)
});
```

---

## Project Implementation

### API Client Location

Location: `src/frontend/src/lib/api/client.ts`

### Base URL Configuration

```typescript
const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error('VITE_API_URL environment variable is not set');
}
```

### Standard Headers

```typescript
const headers = {
  'Content-Type': 'application/json',
  // Add session headers if needed
};
```

### Common Endpoints

| Purpose | Method | Endpoint |
|---------|--------|----------|
| List pipelines | GET | `/api/pipelines` |
| Get pipeline | GET | `/api/pipelines/{id}` |
| Create pipeline | POST | `/api/pipelines` |
| Update pipeline | PUT | `/api/pipelines/{id}` |
| Delete pipeline | DELETE | `/api/pipelines/{id}` |
| Health check | GET | `/health` |
