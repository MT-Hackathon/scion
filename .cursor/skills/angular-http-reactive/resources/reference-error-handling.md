# Reference: Error Handling

Standardized error handling strategies for the procurement application.

---

## HTTP Status Code Handling

| Status Code | Description | Strategy | User Message |
|-------------|-------------|----------|--------------|
| **400** | Bad Request | Validation error. Show specific field errors if available. | "Please check your input and try again." |
| **401** | Unauthorized | Authentication required. Redirect to login. | "Session expired. Please log in again." |
| **403** | Forbidden | Insufficient permissions. Show access denied page. | "You do not have permission to perform this action." |
| **404** | Not Found | Resource missing. Redirect to list or 404 page. | "The requested item was not found." |
| **409** | Conflict | Optimistic locking or duplicate resource. | "This record has been modified by another user." |
| **422** | Unprocessable Entity | Business logic validation failure. | Specific business error message. |
| **500** | Server Error | Unhandled server exception. Log and show generic error. | "A server error occurred. Please try again later." |
| **503** | Service Unavailable | Server maintenance or overload. Retry later. | "Service is temporarily unavailable." |

---

## Functional Error Interceptor

A global interceptor to catch and process HTTP errors.

```typescript
/**
 * Global HTTP error interceptor.
 */
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { NotificationService } from '@core/services/notification.service';
import { AuthService } from '@core/services/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const notificationService = inject(NotificationService);
  const authService = inject(AuthService);
  const errorExtractor = inject(ErrorExtractorService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      const errorMessage = errorExtractor.extract(error);

      if (error.status === 401) {
        authService.logout();
      }

      notificationService.showError(errorMessage);
      
      // Re-throw the error so the calling service can also handle it
      return throwError(() => error);
    })
  );
};
```

---

## Retry Strategies

Use the `retry` operator for transient failures like network timeouts or 503 errors.

```typescript
/**
 * Exponential backoff retry strategy for transient errors.
 */
import { retry, timer } from 'rxjs';

export const transientErrorRetry = retry({
  count: 3,
  delay: (error, retryCount) => {
    // Only retry on transient errors (0 = network, 503 = service unavailable, 504 = gateway timeout)
    const transientStatuses = [0, 503, 504];
    if (transientStatuses.includes(error.status)) {
      return timer(Math.pow(2, retryCount - 1) * 1000); // 1s, 2s, 4s
    }
    // Don't retry for 4xx errors
    throw error;
  }
});
```

---

## User-Friendly Error Messages

Avoid technical jargon in error messages. Map API error codes to human-readable strings.

```typescript
/**
 * Mapping API error codes to user-friendly messages.
 */
const ERROR_MAP: Record<string, string> = {
  'ERR_INSUFFICIENT_FUNDS': 'The budget for this department is insufficient.',
  'ERR_VENDOR_INACTIVE': 'This vendor is no longer active in our system.',
  'ERR_DUPLICATE_PO': 'A purchase order with this number already exists.'
};

function getFriendlyMessage(apiErrorCode: string): string {
  return ERROR_MAP[apiErrorCode] || 'An error occurred during processing.';
}
```
