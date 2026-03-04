# Checklist: Memory Leaks

Procedures for preventing and detecting memory leaks in RxJS-heavy code.

## Modern Pattern (Angular 21+)
The primary defense against memory leaks is `takeUntilDestroyed(this.destroyRef)`:

```typescript
private readonly destroyRef = inject(DestroyRef);

constructor() {
  this.observable$.pipe(
    takeUntilDestroyed(this.destroyRef)
  ).subscribe({ ... });
}
```

For state that templates consume, prefer `toSignal()` over subscriptions.

---

## Subscription Cleanup

- [ ] Every explicit `.subscribe()` call has a corresponding unsubscription logic.
- [ ] Components use `takeUntilDestroyed` from `@angular/core/rxjs-interop` for automated cleanup.
- [ ] If `takeUntilDestroyed` is used outside the constructor, the `DestroyRef` is explicitly provided.
- [ ] ~~`Subscription` objects are stored in an array or `Subscription` group and cleaned up in `ngOnDestroy` (legacy pattern).~~
- [ ] **[DEPRECATED]** Legacy subscription arrays with `ngOnDestroy` - migrate to `takeUntilDestroyed(this.destroyRef)`.

---

## Template Patterns

- [ ] Signals via `toSignal()` are used for component state (PREFERRED).
- [ ] `async` pipe with `@if` is used only when signals are not appropriate (legacy code, complex operator chains).
- [ ] Nested `async` pipes are avoided: `@if (data$ | async; as data) { ... }`.
- [ ] `@for` loops use signals or async pipe for observable data.

---

## Service Patterns

- [ ] Services do not hold onto subscriptions indefinitely unless they are intended to live for the app lifecycle.
- [ ] Long-lived subjects in services are properly managed (avoiding "leaky" subjects).
- [ ] `shareReplay(1)` is used with caution; ensure it doesn't prevent the source observable from completing if needed.
- [ ] API services return observables and don't subscribe internally unless necessary for side-effects.

---

## Common Red Flags

- [ ] Multiple subscriptions to the same observable in one component (use `share()` or `shareReplay()`).
- [ ] For HTTP request deduplication, use `idempotentLoad` utility from `core/utils/`.
- [ ] Subscriptions inside other subscriptions (use flattening operators like `switchMap`, `mergeMap`).
- [ ] Forgetting to unsubscribe from `router.events` or other global streams.
- [ ] Using `BehaviorSubject` for everything (prefer standard `Subject` or `Signals` where appropriate).

---

## Testing for Leaks

- [ ] Verify that subscriptions are closed when components are destroyed in unit tests.
- [ ] Use Chrome DevTools "Memory" tab to take heap snapshots and look for detached DOM nodes.
- [ ] Check for increasing counts of `Subscriber` objects in the heap profile.
- [ ] Monitor the "Task Manager" or "Performance" tab for memory growth during repeated navigation.
