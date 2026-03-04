# Examples: HTTP Client

Implementation patterns for base services, domain services, and loading states in the procurement app.

---

## Base API Service

The base service provides common HTTP methods with typed responses and consistent endpoint handling.

```typescript
/**
 * Base API service providing core HTTP functionality.
 * Use this as a foundation for domain-specific services.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { apiConfig } from '@env/environment';

@Injectable({ providedIn: 'root' })
export class BaseApiService {
  protected readonly http = inject(HttpClient);
  protected readonly baseUrl = apiConfig.baseUrl;

  /**
   * Performs a GET request.
   * @param endpoint The API endpoint (e.g., '/items')
   * @param params Optional query parameters
   */
  protected get<T>(endpoint: string, params?: HttpParams): Observable<T> {
    return this.http.get<T>(`${this.baseUrl}${endpoint}`, { params });
  }

  /**
   * Performs a POST request.
   * @param endpoint The API endpoint
   * @param body The request body
   */
  protected post<T>(endpoint: string, body: unknown): Observable<T> {
    return this.http.post<T>(`${this.baseUrl}${endpoint}`, body);
  }

  /**
   * Performs a PUT request.
   * @param endpoint The API endpoint
   * @param body The request body
   */
  protected put<T>(endpoint: string, body: unknown): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}${endpoint}`, body);
  }

  /**
   * Performs a DELETE request.
   * @param endpoint The API endpoint
   */
  protected delete<T>(endpoint: string): Observable<T> {
    return this.http.delete<T>(`${this.baseUrl}${endpoint}`);
  }
}
```

---

## Domain Data Service

Domain-specific services extend `BaseApiService` to provide high-level methods for business logic.

```typescript
/**
 * Purchase Order service handling procurement-specific data.
 */
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from './base-api.service';
import { PurchaseOrder } from '@core/models/purchase-order.model';

@Injectable({ providedIn: 'root' })
export class PurchaseOrderService extends BaseApiService {
  /**
   * Retrieves a list of purchase orders.
   */
  getOrders(): Observable<PurchaseOrder[]> {
    return this.get<PurchaseOrder[]>('/purchase-orders');
  }

  /**
   * Creates a new purchase order.
   * @param order The order data to create
   */
  createOrder(order: Partial<PurchaseOrder>): Observable<PurchaseOrder> {
    return this.post<PurchaseOrder>('/purchase-orders', order);
  }

  /**
   * Updates an existing purchase order.
   * @param id The order ID
   * @param order The updated order data
   */
  updateOrder(id: string, order: Partial<PurchaseOrder>): Observable<PurchaseOrder> {
    return this.put<PurchaseOrder>(`/purchase-orders/${id}`, order);
  }
}
```

---

## Loading State Management

Manage loading states using signals for reactive UI updates.

```typescript
/**
 * Component managing procurement data with loading states.
 */
import {Component, inject, signal, ChangeDetectionStrategy, DestroyRef} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {PurchaseOrderService} from '@core/services/purchase-order.service';
import {NotificationService} from '@core/services/notification.service';
import {finalize} from 'rxjs';

@Component({
  selector: 'app-order-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (isLoading()) {
      <mat-spinner />
    } @else {
      <!-- Render order list -->
    }
  `
})
export class OrderListComponent {
  private readonly orderService = inject(PurchaseOrderService);
  private readonly notification = inject(NotificationService);
  private readonly errorExtractor = inject(ErrorExtractorService);
  private readonly destroyRef = inject(DestroyRef);
  
  readonly orders = signal<PurchaseOrder[]>([]);
  readonly isLoading = signal(false);

  loadOrders(): void {
    this.isLoading.set(true);
    
    this.orderService.getOrders()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.isLoading.set(false))
      )
      .subscribe({
        next: (data) => this.orders.set(data),
        error: (error: Error) => this.notification.showError(this.errorExtractor.extract(error)),
      });
  }
}
```

---

## Request Cancellation

Use `switchMap` or `takeUntilDestroyed` to handle request cancellation.

```typescript
/**
 * Component demonstrating request cancellation on search.
 */
import { Component, inject } from '@angular/core';
import { FormControl } from '@angular/forms';
import { toSignal } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { ItemService } from '@core/services/item.service';

@Component({...})
export class ItemSearchComponent {
  private readonly itemService = inject(ItemService);
  
  readonly searchControl = new FormControl('');

  // switchMap automatically cancels the previous HTTP request when the input changes
  readonly items = toSignal(
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(query => this.itemService.searchItems(query ?? ''))
    ),
    { initialValue: [] }
  );
}
```
