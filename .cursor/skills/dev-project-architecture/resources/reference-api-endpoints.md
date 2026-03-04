# Procurement API Endpoints Reference

Quick reference for `procurement-api` endpoints consumed by `procurement-web`.

## API Configuration

**Base URL Configuration:** `src/environments/environment.ts`

```typescript
export const apiConfig = {
  baseUrl: '/api',           // Proxied to backend in dev, absolute in prod
  mockEnabled: true,         // Toggle for mock vs real API
};
```

**DI Token Pattern:** Services should inject `API_BASE_URL` token rather than importing `apiConfig` directly:

```typescript
// In app.config.ts
import { InjectionToken } from '@angular/core';
import { apiConfig } from '@env/environment';

export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL');

providers: [
  { provide: API_BASE_URL, useValue: apiConfig.baseUrl },
]
```

## Core Endpoints

| Domain | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| Requisitions | `/requisitions` | GET | List all requisitions |
| Requisitions | `/requisitions/{id}` | GET | Get requisition by ID |
| Requisitions | `/requisitions` | POST | Create new requisition |
| Orders | `/orders` | GET | List all orders |
| Orders | `/orders/{id}` | GET | Get order by ID |
| Vendors | `/vendors` | GET | List all vendors |
| Vendors | `/vendors/{id}` | GET | Get vendor by ID |
| Contracts | `/contracts` | GET | List all contracts |

## Authentication

- **Provider:** Okta (shared across web and api)
- **Token Type:** Bearer JWT
- **Header:** `Authorization: Bearer {access_token}`

## Related Files

- **Okta Config:** `src/environments/environment.ts` (oktaConfig)
- **API Config:** `src/environments/environment.ts` (apiConfig)
- **Configuration Service:** `src/app/core/configuration/configuration.service.ts`
- **HTTP Interceptor:** `src/app/core/interceptor/token-interceptor.ts` (auth token injection)

## Cross-Repository Notes

- API source: `procurement-api` repository
- API tech stack: Spring Boot 4.0, Java 25, PostgreSQL
- API docs: Check `procurement-api/README.md` or Swagger UI when running
