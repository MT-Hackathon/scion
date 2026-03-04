// BLUEPRINT: http-error-interceptor
// STRUCTURAL: HttpInterceptorFn signature, inject pattern, catchError with mandatory re-throw, telemetry hook
// ILLUSTRATIVE: LoggerService, AuthService, specific status code branches (customize for your app's services)

import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { LoggerService } from '@core/services/logger.service';   // ILLUSTRATIVE: your structured logger
import { AuthService } from '@core/services/auth.service';       // ILLUSTRATIVE: your auth service

export const httpErrorInterceptor: HttpInterceptorFn = (req, next) => {
  const logger = inject(LoggerService);      // ILLUSTRATIVE
  const authService = inject(AuthService);   // ILLUSTRATIVE

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Telemetry: always log with correlation context before branching
      logger.error('HTTP Error', { url: req.url, status: error.status }); // ILLUSTRATIVE

      // Auth boundary: clear session and redirect on 401
      if (error.status === 401) {
        authService.logout(); // ILLUSTRATIVE
      }

      // MANDATE: re-throw ALL errors so service layers and GlobalErrorHandler receive them.
      // Map business states (404, 409, 422) to result types at the service boundary, not here.
      return throwError(() => error);
    })
  );
};
