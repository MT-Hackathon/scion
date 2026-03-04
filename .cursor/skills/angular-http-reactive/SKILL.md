---
name: angular-http-reactive
description: "Governs Angular HttpClient patterns and RxJS operators: switchMap, catchError, retry, interceptors, and Observable pipelines for API services. Use when implementing API services, HTTP interceptors, or async reactive data streams. DO NOT use for authentication flows (see security) or testing HTTP calls (see angular-testing)."
---

<ANCHORSKILL-HTTP-REACTIVE>

# Angular HTTP & Reactive Patterns

## Contents

- [1. Foundation: Configuration & API Services](#1-foundation-configuration--api-services)
- [2. Functional Interceptors](#2-functional-interceptors-telemetry--retry)
- [3. RxJS Operator Selection](#3-rxjs-operator-selection-mandated)
- [4. Signal & RxJS Interop](#4-signal--rxjs-interop)
- [5. Memory Leak Prevention](#5-memory-leak-prevention--safety)
- [6. Prohibited Patterns](#6-prohibited-patterns)
- [Resources](#resources)

## 1. Foundation: Configuration & API Services

Configure `HttpClient` in `app.config.ts` using functional interceptors. Centralize API calls in typed services.

### 1.1 Circular Dependency Prevention (MANDATED)

- **InjectionTokens**: Move `InjectionToken` definitions to standalone files (e.g., `src/app/core/config/api-tokens.ts`) to avoid transitive cycles.
- **Config Files**: Avoid importing services into `app.config.ts`. If a provider needs a service, use the `deps: [Service]` pattern in the provider object instead of top-level imports.

```typescript
// app.config.ts (MANDATED ORDER)
export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([
      tokenInterceptor,      // 1. Adds W3C traceparent header
      httpErrorInterceptor,  // 2. Telemetry: Logs 4xx/5xx with traceId
      authErrorInterceptor,  // 3. Identity: 401/403 handling
      activeRoleInterceptor  // 4. Multi-tenancy: X-Active-Role header
    ]))
  ],
};

// base-api.service.ts
@Injectable({providedIn: 'root'})
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = apiConfig.baseUrl;

  get<T>(endpoint: string): Observable<T> {
    return this.http.get<T>(`${this.baseUrl}${endpoint}`);
  }
  post<T>(endpoint: string, body: unknown): Observable<T> {
    return this.http.post<T>(`${this.baseUrl}${endpoint}`, body);
  }
}
```

## 2. Functional Interceptors (Telemetry & Retry)

Interceptors must prioritize telemetry and correlation via `LoggerService` and `trace-id.util.ts`.

```typescript
export const httpErrorInterceptor: HttpInterceptorFn = (req, next) => {
  const logger = inject(LoggerService);
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Structured context: status, traceId, problemDetail
      logger.error('API Failure', { url: req.url, status: error.status });
      // Re-throw based on error category
      if (error.status === 404) {
        // Business state: Let service boundary map to result type
        return throwError(() => error); 
      }
      if ([401, 403].includes(error.status)) {
        // Auth failure: Handled by dedicated interceptor
        return throwError(() => error);
      }
      // Infrastructure failures (500, network, timeout): Always re-throw for GlobalErrorHandler
      return throwError(() => error);
    })
  );
};

export const retryInterceptor: HttpInterceptorFn = (req, next) => 
  next(req).pipe(
    retry({
      count: 3,
      delay: (_, retryCount) => timer(Math.pow(2, retryCount - 1) * 1000), // 1s, 2s, 4s
      resetOnSuccess: true
    })
  );
```

## 3. RxJS Operator Selection (MANDATED)

| Scenario | Operator | Why |
|----------|----------|-----|
| User Search | `switchMap` | Cancels previous pending requests |
| Form Submit | `exhaustMap` | Ignores clicks until request completes |
| Parallel Calls | `forkJoin` | Waits for all; equivalent to Promise.all |
| Sequential Calls | `concatMap` | Ensures strict ordering |
| Result Caching | `shareReplay(1)`| Prevents duplicate network hits |

## 4. Signal & RxJS Interop

Prefer Signals for template state. Use `toSignal` for consumption and `toObservable` for reactive triggers.

```typescript
@Component({...})
export class DataComponent {
  private readonly dataService = inject(DataService);
  private readonly filter = signal({ status: 'active' });
  private readonly refresh$ = new Subject<void>();

  // Pattern A: State-driven (Filter change triggers request)
  readonly data = toSignal(
    toObservable(this.filter).pipe(
      switchMap(f => this.dataService.getData(f))
    ), { initialValue: [] }
  );

  // Pattern B: Event-driven (Button click triggers refresh)
  readonly items = toSignal(
    this.refresh$.pipe(
      startWith(undefined),
      switchMap(() => this.dataService.getItems())
    ), { initialValue: [] }
  );
}
```

## 5. Memory Leak Prevention & Safety

Always cleanup manual subscriptions using `takeUntilDestroyed`. Prefer the `async` pipe or `toSignal` for automatic lifecycle management.

```typescript
@Component({...})
export class SafeComponent {
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit() {
    this.service.events$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(e => this.handle(e));
  }
}
```

## 6. Prohibited Patterns

- **No cleanup**: Subscribing in services/components without `takeUntilDestroyed` or `unsubscribe`.
- **Manual Subscribe**: Using `.subscribe()` in components when `| async` or `toSignal()` suffices.
- **Untyped Responses**: Using `any` for HTTP returns; always define interfaces.
- **Swallowing Errors**: Using `catchError` without re-throwing (`throwError`) for infrastructure failures (500, network, timeout).
  - **WRONG**: `catchError(() => of(null))` for business states (untyped, loses context).
  - **VALID**: Mapping business outcomes (404 -> result type) at the service boundary.
  - **GOOD**: `catchError(err => err.status === 404 ? of({ status: 'not_found' }) : throwError(() => err))` (typed, preserves infrastructure errors).

## Resources

- [Cross-References](resources/cross-references.md) — adjacent skills, shared utilities, and external docs
- [Examples: HTTP Client](resources/examples-http-client.md) — base service, domain service, loading state, request cancellation
- [Examples: RxJS Operators](resources/examples-rxjs-operators.md) — switchMap, exhaustMap, forkJoin, shareReplay, debounce patterns
- [Reference: Error Handling](resources/reference-error-handling.md) — HTTP status strategies, retry config, user-message mapping
- [Checklist: Memory Leaks](resources/checklist-memory-leaks.md) — subscription hygiene, template patterns, testing for leaks
- [Blueprint: BaseApiService](blueprints/base-api.service.ts) — structural base HTTP service for extension
- [Blueprint: HTTP Error Interceptor](blueprints/http-error.interceptor.ts) — functional interceptor scaffold

</ANCHORSKILL-HTTP-REACTIVE>
