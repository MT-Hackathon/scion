# Examples: Credential Handling

Credential storage and management patterns.

---

## Pattern

### Never Store in Browser

```typescript
// ❌ BAD: Storing credentials in browser
localStorage.setItem('api_key', apiKey);
sessionStorage.setItem('token', token);

// ✅ GOOD: Send to backend immediately
async function saveCredential(apiKey: string) {
  const response = await fetch(`${API_URL}/api/credentials`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key_ref: 'my_api', value: apiKey })
  });
  
  if (response.ok) {
    // Clear from memory
    apiKey = '';
  }
}
```

### Delete via Backend

```typescript
async function deleteCredential(keyRef: string) {
  await fetch(`${API_URL}/api/credentials/${keyRef}`, {
    method: 'DELETE'
  });
}
```

### Exposure Mitigation

```typescript
// Mask credentials in logs
function logApiCall(url: string, apiKey: string) {
  // ❌ BAD: Full credential in logs
  console.log(`Calling ${url} with key ${apiKey}`);
  
  // ✅ GOOD: Masked credential
  const masked = apiKey.substring(0, 4) + '***';
  console.log(`Calling ${url} with key ${masked}`);
}
```

### Error Message Safety

```typescript
async function testEndpoint(url: string, apiKey: string) {
  try {
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${apiKey}` }
    });
    
    if (!response.ok) {
      // ❌ BAD: Credential in error
      throw new Error(`Failed with key ${apiKey}`);
      
      // ✅ GOOD: No credential in error
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  } catch (err) {
    return { success: false, error: err.message };
  }
}
```

### Credential Placement

```typescript
// ❌ BAD: Credential in URL
const url = `https://api.example.com/data?api_key=${apiKey}`;

// ✅ GOOD: Credential in header
const response = await fetch('https://api.example.com/data', {
  headers: { 'Authorization': `Bearer ${apiKey}` }
});
```

---

## Project Implementation

### Credential Backend Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Store | POST | `/api/credentials` |
| Delete | DELETE | `/api/credentials/{key_ref}` |
| Test | POST | `/api/connections/test` |

### Test Connection Pattern

For test connections, use credential references (not actual values):

```typescript
async function testCredentials(config: ApiConfig) {
  const response = await fetch(`${API_URL}/api/connections/test`, {
    method: 'POST',
    body: JSON.stringify({
      url: config.url,
      credential_ref: config.credential_ref // Reference only
    })
  });
  
  return response.json();
}
```
