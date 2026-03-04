# Reference: HTTP Response Envelope

Standard API response format.

---

## Pattern

### Response Envelope Structure

All backend responses follow this envelope:

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}
```

### Success Response

```json
{
  "success": true,
  "data": {
    "id": "123",
    "name": "My Pipeline"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid pipeline configuration"
  }
}
```

### Type-Safe Handling

```typescript
async function fetchPipelines(): Promise<Pipeline[]> {
  const response = await fetch(`${API_URL}/api/pipelines`);
  const result: ApiResponse<Pipeline[]> = await response.json();
  
  if (!result.success || !result.data) {
    throw new Error(result.error?.message || 'Failed to fetch');
  }
  
  return result.data;
}
```

### Error Surface Pattern

Always surface errors to the user—never mask or swallow:

```typescript
try {
  const data = await fetchPipelines();
  // Use data
} catch (err) {
  // Show error to user
  showErrorBanner(err.message);
}
```

---

## Project Implementation

### Base URL Configuration

```typescript
// src/lib/api/client.ts
const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  throw new Error('VITE_API_URL not set');
}
```

### API Client Helper

```typescript
export async function apiCall<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers
    }
  });
  
  const result: ApiResponse<T> = await response.json();
  
  if (!result.success) {
    throw new Error(result.error?.message || 'API call failed');
  }
  
  return result.data!;
}
```

### Backend Verification

Check backend health before blaming UI:

```typescript
async function checkBackendHealth(): Promise<boolean> {
  try {
    await fetch(`${API_URL}/health`, { 
      signal: AbortSignal.timeout(5000) 
    });
    return true;
  } catch {
    showErrorBanner('Cannot connect to backend');
    return false;
  }
}
```
