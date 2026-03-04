# Examples: Audit Logging

## Audit Event Interface

```typescript
/** Represents a single field change for audit tracking */
export interface AuditChange {
  field: string;
  oldValue: unknown;
  newValue: unknown;
}

/** Audit event structure - server assigns id, timestamp, sessionId */
export interface AuditEvent {
  id: string;
  actorId: string;
  role: string;
  sessionId: string;
  timestamp: string;
  action: 'create' | 'update' | 'delete' | 'approve' | 'reject';
  resource: string;
  resourceId?: string;
  changes?: AuditChange[];
  metadata?: Record<string, unknown>;
}
```

## Audit Service Implementation

**Note**: The backend is authoritative for audit records. The frontend sends audit requests; the server assigns `id`, `timestamp`, and `sessionId`.

```typescript
import {Injectable, inject} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable} from 'rxjs';
import {environment} from '@env/environment';

type AuditPayload = Omit<AuditEvent, 'id' | 'timestamp' | 'sessionId'>;

@Injectable({providedIn: 'root'})
export class AuditService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/audit`;

  /** Send audit event to server. Caller should subscribe and handle errors. */
  logEvent(event: AuditPayload): Observable<AuditEvent> {
    const sanitizedEvent = this.redactPII(event);
    return this.http.post<AuditEvent>(this.apiUrl, sanitizedEvent);
  }

  private redactPII(event: AuditPayload): AuditPayload {
    const sensitiveFields = ['email', 'ssn', 'phoneNumber'];
    if (!event.changes) return event;
    
    return {
      ...event,
      changes: event.changes.map(change =>
        sensitiveFields.includes(change.field)
          ? {...change, oldValue: '***', newValue: '***'}
          : change
      ),
    };
  }
}
```

## Logging Interceptor for API Calls

```typescript
import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap } from 'rxjs/operators';
import { AuditService } from './audit.service';

export const auditInterceptor: HttpInterceptorFn = (req, next) => {
  const auditService = inject(AuditService);
  
  // Only log state-changing requests
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(req.method)) {
    return next(req).pipe(
      tap({
        next: (event) => {
          if (event instanceof HttpResponse && event.status >= 200 && event.status < 300) {
            auditService.logEvent({
              actorId: 'system', // Get from auth service
              role: 'user',       // Get from auth service
              action: req.method === 'POST' ? 'create' : req.method === 'DELETE' ? 'delete' : 'update',
              resource: req.url,
              changes: [{ field: 'requestBody', oldValue: null, newValue: req.body }]
            });
          }
        }
      })
    );
  }
  return next(req);
};
```

## Change Tracking for Entities

```typescript
/** Compares two entities and returns a list of changed fields */
export function trackChanges<T extends Record<string, unknown>>(
  oldEntity: T,
  newEntity: T
): AuditChange[] {
  const changes: AuditChange[] = [];
  
  for (const key in newEntity) {
    if (!Object.prototype.hasOwnProperty.call(newEntity, key)) continue;
    
    const oldValue = oldEntity[key];
    const newValue = newEntity[key];
    
    if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
      changes.push({field: key, oldValue, newValue});
    }
  }
  
  return changes;
}
```
