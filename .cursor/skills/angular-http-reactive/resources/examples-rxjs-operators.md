# Examples: RxJS Operators

Common RxJS operator patterns for handling HTTP streams in the procurement application.

---

## switchMap: Search and Typeahead

Cancels the previous internal observable when a new value is emitted from the source. Ideal for search results.

```typescript
/**
 * Reactive search implementation using switchMap.
 * Use toSignal() or takeUntilDestroyed() for proper cleanup.
 */
readonly searchResults = toSignal(
  this.searchControl.valueChanges.pipe(
    debounceTime(300), // Wait for user to stop typing
    distinctUntilChanged(), // Only if the value actually changed
    switchMap(query => this.apiService.search(query)) // Previous request is cancelled
  ),
  {initialValue: []}
);
```

---

## exhaustMap: Form Submission

Ignores new source values while the internal observable is still active. Perfect for preventing double-submits.

```typescript
/**
 * Preventing duplicate form submissions using exhaustMap.
 * Subscribe in ngOnInit with takeUntilDestroyed for cleanup.
 */
private readonly destroyRef = inject(DestroyRef);
private readonly errorExtractor = inject(ErrorExtractorService);
private readonly submitSubject = new Subject<FormData>();

ngOnInit(): void {
  this.submitSubject.pipe(
    takeUntilDestroyed(this.destroyRef),
    exhaustMap(formData => this.orderService.createOrder(formData))
  ).subscribe({
    next: () => this.router.navigate(['/success']),
    error: (error: Error) => this.notification.showError(this.errorExtractor.extract(error)),
  });
  
  // NOTE: For complex mutations, consider runCrudMutation for standardized success/error side effects.
}

onSubmit(): void {
  this.submitSubject.next(this.form.value);
}
```

---

## forkJoin: Parallel Requests

Combines multiple observables and waits for all to complete. Emits an array of results. Similar to `Promise.all`.

```typescript
/**
 * Loading dashboard data from multiple endpoints in parallel.
 * Use takeUntilDestroyed for cleanup.
 */
loadDashboardData(): void {
  forkJoin({
    orders: this.orderService.getPendingOrders(),
    vendors: this.vendorService.getActiveVendors(),
    inventory: this.inventoryService.getLowStockItems()
  }).pipe(
    takeUntilDestroyed(this.destroyRef)
  ).subscribe({
    next: ({orders, vendors, inventory}) => {
      this.dashboardData.set({orders, vendors, inventory});
    },
    error: (error: Error) => this.notification.showError(this.errorExtractor.extract(error)),
  });
}
```

---

## shareReplay: Caching and Sharing

Shares a single subscription among multiple subscribers and replays the last value to new subscribers.

```typescript
/**
 * Service-level caching for reference data.
 */
@Injectable({ providedIn: 'root' })
export class ReferenceDataService {
  // The request is made only once; subsequent subscribers get the cached value
  private readonly categories$ = this.apiService.get('/categories').pipe(
    shareReplay(1)
  );

  getCategories() {
    return this.categories$;
  }
}

/**
 * NOTE: For advanced cache management and in-flight request deduplication,
 * use the idempotentLoad utility to manage cache hits and shared observables.
 */
```

---

## debounceTime + distinctUntilChanged: Input Optimization

Reduces the number of emissions from an input stream to improve performance.

```typescript
/**
 * Optimizing auto-save or search inputs.
 * Prefer toSignal() for declarative reactive state.
 */
readonly filterValue = toSignal(
  this.filterControl.valueChanges.pipe(
    debounceTime(400),
    distinctUntilChanged()
  ),
  {initialValue: ''}
);

// Use computed() or effect() to react to filter changes
readonly filteredItems = computed(() => {
  const filter = this.filterValue();
  return this.allItems().filter(item => item.name.includes(filter));
});
```

---

## sequential vs Parallel Requests

| Pattern | Operator | Behavior |
|---------|----------|----------|
| **Sequential** | `concatMap` | Process items one after another in order. |
| **Parallel** | `forkJoin` | Run all at once, wait for all to finish. |
| **Latest Only** | `switchMap` | Only care about the result of the most recent request. |
| **Ignore New** | `exhaustMap` | Don't allow new requests until current one is done. |
