# Examples: Payload Validation

HTTP payload validation and sanitization patterns.

---

## Pattern

### Zod Schema Validation

```typescript
import { z } from 'zod';

const pipelineSchema = z.object({
  name: z.string().min(1).max(100),
  nodes: z.array(z.object({
    id: z.string(),
    type: z.enum(['apiSource', 'transform', 'databaseTarget'])
  })).max(1000)
});

async function savePipeline(pipeline: unknown) {
  // ❌ BAD: No validation
  await fetch(`${API_URL}/api/pipelines`, {
    method: 'POST',
    body: JSON.stringify(pipeline)
  });
  
  // ✅ GOOD: Validate first
  const result = pipelineSchema.safeParse(pipeline);
  if (!result.success) {
    throw new Error('Invalid pipeline data');
  }
  
  // Check size
  const payload = JSON.stringify(result.data);
  if (payload.length > 1_000_000) { // 1MB
    throw new Error('Payload too large (max 1MB)');
  }
  
  await fetch(`${API_URL}/api/pipelines`, {
    method: 'POST',
    body: payload,
    headers: { 'Content-Type': 'application/json' }
  });
}
```

### Input Sanitization

```typescript
function sanitizeInput(input: string): string {
  // Remove null bytes
  let clean = input.replace(/\0/g, '');
  
  // Trim whitespace
  clean = clean.trim();
  
  // Limit length
  clean = clean.substring(0, 10000);
  
  return clean;
}

async function createResource(name: string, description: string) {
  // ❌ BAD: Using raw input
  await fetch(`${API_URL}/api/resources`, {
    method: 'POST',
    body: JSON.stringify({ name, description })
  });
  
  // ✅ GOOD: Sanitize first
  const sanitized = {
    name: sanitizeInput(name),
    description: sanitizeInput(description)
  };
  
  await fetch(`${API_URL}/api/resources`, {
    method: 'POST',
    body: JSON.stringify(sanitized)
  });
}
```

### Browser API Limits

```typescript
// ❌ BAD: Direct disk access (Tauri)
import { invoke } from '@tauri-apps/api';
const data = await invoke('write_file', { path: '/path/to/file', content });

// ✅ GOOD: Browser file download
function downloadFile(content: string, filename: string) {
  const blob = new Blob([content], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// ✅ GOOD: Backend file API
async function saveFile(content: string, filename: string) {
  await fetch(`${API_URL}/api/files`, {
    method: 'POST',
    body: JSON.stringify({ filename, content })
  });
}

// ✅ GOOD: Native file input
<input type="file" onchange={handleFileUpload} />
```

---

## Project Implementation

### Payload Size Limits

| Type | Max Size |
|------|----------|
| Standard payload | 1MB |
| File upload | Backend-defined |
| Auto-save | 5MB |

### Sanitization Utils

Location: `app/frontend/src/lib/utils/sanitization.ts` (if exists)

Common sanitization functions for:
- Null byte removal
- Whitespace trimming
- Length limiting
- Special character handling
