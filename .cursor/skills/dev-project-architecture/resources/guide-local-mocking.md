# Local Mocking Guide

How to develop frontend features before the backend is ready using the DI-level mock pattern.

---

## Overview

The mock pattern uses Angular's dependency injection to swap between mock and real API implementations at the provider level. This avoids `if (mockEnabled)` checks scattered throughout services.

---

## Architecture Pattern

```
                  ┌─────────────────┐
                  │   Component     │
                  └────────┬────────┘
                           │ injects
                           ▼
                  ┌─────────────────┐
                  │  Service Token  │  (e.g., ConfigurationApi)
                  └────────┬────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
  ┌─────────────────┐            ┌─────────────────┐
  │ RealApiService  │            │ MockApiService  │
  │ (HTTP calls)    │            │ (Observable.of) │
  └─────────────────┘            └─────────────────┘
```

---

## Implementation Steps

### 1. Define the Interface

Create an abstract class or interface that defines the API contract:

```typescript
// configuration.api.ts
export abstract class ConfigurationApi {
  abstract loadConfiguration(): Observable<AppConfiguration>;
  abstract getThresholds(): Observable<ThresholdConfiguration>;
}
```

### 2. Create Real Implementation

The service that makes actual HTTP calls:

```typescript
// configuration-http.service.ts
@Injectable()
export class ConfigurationHttpService extends ConfigurationApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  loadConfiguration(): Observable<AppConfiguration> {
    return this.http.get<AppConfiguration>(`${this.baseUrl}/config`);
  }

  getThresholds(): Observable<ThresholdConfiguration> {
    return this.http.get<ThresholdConfiguration>(`${this.baseUrl}/config/thresholds`);
  }
}
```

### 3. Create Mock Implementation

Returns mock data without HTTP calls:

```typescript
// configuration-mock.service.ts
@Injectable()
export class ConfigurationMockService extends ConfigurationApi {
  loadConfiguration(): Observable<AppConfiguration> {
    return of(MOCK_CONFIGURATION).pipe(delay(200)); // Simulate network
  }

  getThresholds(): Observable<ThresholdConfiguration> {
    return of(MOCK_CONFIGURATION.thresholds).pipe(delay(100));
  }
}
```

### 4. Configure DI Provider

In `app.config.ts`, conditionally provide the implementation:

```typescript
import { apiConfig } from '@env/environment';
import { ConfigurationApi } from '@core/configuration/configuration.api';
import { ConfigurationHttpService } from '@core/configuration/configuration-http.service';
import { ConfigurationMockService } from '@core/configuration/configuration-mock.service';

providers: [
  {
    provide: ConfigurationApi,
    useClass: apiConfig.mockEnabled
      ? ConfigurationMockService
      : ConfigurationHttpService,
  },
]
```

---

## Toggle Mock Mode

Change the flag in `src/environments/environment.ts`:

```typescript
export const apiConfig = {
  baseUrl: '/api',
  mockEnabled: true,   // true = mock, false = real API
};
```

**For production builds:** Create `environment.prod.ts` with `mockEnabled: false`.

---

## Best Practices

1. **Add realistic delays** - Use `delay()` operator in mocks to simulate network latency
2. **Match real response shapes exactly** - Mock data should match API contracts
3. **Test both modes** - Periodically verify real API integration works
4. **Use mock for demos** - Keep mock mode for stakeholder demos when backend is unstable

---

## When to Use Each Pattern

| Situation | Pattern |
|-----------|---------|
| Unit tests | Vitest mocks (`vi.fn()`) |
| Local dev without backend | DI mock services |
| Integration tests | HTTP testing module |
| E2E tests | Real backend or MSW |

---

## Related Resources

- [reference-api-endpoints.md](reference-api-endpoints.md) - API endpoint reference
- [template-api-contract.md](template-api-contract.md) - Contract definition patterns
- [angular-testing/reference-mock-patterns.md](../../angular-testing/resources/reference-mock-patterns.md) - Unit test mocking
