# Reference: Authentication Patterns

Authentication implementation patterns for Angular and API integrations.

---

## Angular/Okta Authentication (PRIMARY)

### Okta Configuration

```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  oktaConfig: {
    issuer: 'https://dev-xxxxx.okta.com/oauth2/default',
    clientId: '0oaxxxxxxxxxx',
    redirectUri: window.location.origin + '/login/callback',
    scopes: ['openid', 'profile', 'email'],
  },
};
```

### Backend: UserId Normalization (MANDATED)

When processing JWT claims in Spring Boot:
- Okta sends user identifiers in the case they were registered (often uppercase)
- All userIds MUST be normalized to lowercase before storage or comparison
- Use `DatabaseJwtAuthenticationConverter.extractUserId()` as the single source of truth
- See [Security Skill](../SKILL.md) for the full normalization contract

### HTTP Interceptor for Token Injection

```typescript
// src/app/core/interceptor/token-interceptor.ts
import {HttpInterceptorFn} from '@angular/common/http';
import {inject} from '@angular/core';
import {OKTA_AUTH} from '@okta/okta-angular';

/**
 * Injects Okta access token into outgoing requests.
 * 
 * IMPORTANT: oktaAuth.getAccessToken() is SYNCHRONOUS. 
 * Do NOT wrap in from() or treat as Promise - that emits each character!
 */
export const tokenInterceptor: HttpInterceptorFn = (req, next) => {
  const oktaAuth = inject(OKTA_AUTH);
  const accessToken = oktaAuth.getAccessToken();

  if (!accessToken) {
    return next(req);
  }

  const requestWithHeader = req.clone({
    headers: req.headers.set('Authorization', `Bearer ${accessToken}`),
  });
  return next(requestWithHeader);
};
```

### Registering the Interceptor

```typescript
// app.config.ts or main.ts
import {provideHttpClient, withInterceptors} from '@angular/common/http';
import {tokenInterceptor} from '@core/interceptor/token-interceptor';

export const appConfig = {
  providers: [
    provideHttpClient(withInterceptors([tokenInterceptor])),
  ],
};
```

### Auth Guard Pattern

```typescript
import {inject} from '@angular/core';
import {Router} from '@angular/router';
import {OktaAuthStateService} from '@okta/okta-angular';
import {map} from 'rxjs/operators';

export const authGuard = () => {
  const authStateService = inject(OktaAuthStateService);
  const router = inject(Router);

  return authStateService.authState$.pipe(
    map(authState => {
      if (!authState.isAuthenticated) {
        router.navigate(['/login']);
        return false;
      }
      return true;
    })
  );
};
```

---

## Python Script Authentication (Rule Scripts)

### Header Authentication Pattern

```python
_AUTH_HEADER_BUILDERS: dict[str, Callable[[str], dict]] = {
    "api_key":        lambda ref: {"Authorization": f"Bearer {ref}"},
    "api_key_custom": lambda ref: {"X-API-Key": ref},
    "basic":          lambda ref: {"Authorization": f"Basic {ref}"},
}

def create_auth_headers(credentials_ref: str, auth_type: str) -> dict:
    """Create authentication headers based on type."""
    builder = _AUTH_HEADER_BUILDERS.get(auth_type)
    if builder is None:
        return {}
    return builder(credentials_ref)
```

### Environment Variable Loading

```python
from dotenv import load_dotenv
import os

load_dotenv()

gitlab_token = os.getenv("GITLAB_PERSONAL_ACCESS_TOKEN")
if not gitlab_token:
    raise ValueError("GITLAB_PERSONAL_ACCESS_TOKEN not set")

headers = {"PRIVATE-TOKEN": gitlab_token}
```

---

## Credential Reference Pattern

### Angular - Environment References

```typescript
// GOOD: Config in environment file
import {environment} from '@env/environment';

const apiUrl = environment.apiUrl;
const oktaConfig = environment.oktaConfig;

// BAD: Hardcoded values
const apiUrl = 'https://api.example.com';  // Hardcoded!
```

### Python - Environment References

```python
# GOOD: Reference credentials from environment
config = {
    "url": "https://api.example.com",
    "token_ref": "$ENV{MY_API_KEY}"  # Reference, not value
}

# BAD: Hardcoded credential
config = {
    "url": "https://api.example.com",
    "api_key": "sk-1234567890abcdef"  # Hardcoded!
}
```

---

## Token Handling Best Practices

### Angular

```typescript
// GOOD: Tokens in memory only
export class AuthService {
  private readonly currentToken = signal<string | null>(null);
  
  setToken(token: string): void {
    this.currentToken.set(token);
  }
  
  getToken(): string | null {
    return this.currentToken();
  }
}

// BAD: Token in localStorage
localStorage.setItem('token', token);  // Never do this!
```

### Redacting Tokens in Logs

```typescript
function redactToken(token: string): string {
  if (!token || token.length < 8) return '***';
  return token.substring(0, 4) + '***' + token.substring(token.length - 4);
}

console.log(`Using token: ${redactToken(token)}`);
// Output: Using token: eyJh***xYz0
```
