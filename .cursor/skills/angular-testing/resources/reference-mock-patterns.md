# Reference: Mock Patterns

Common mocking patterns for Angular testing with Vitest.

---

## Mocking Services with Signals

```typescript
import {signal} from '@angular/core';
import {MockedObject} from 'vitest';

// Define signals outside beforeEach for test manipulation
let isLoadingSignal = signal(false);
let dataSignal = signal<Item[]>([]);

let mockService: MockedObject<Partial<DataService>>;

beforeEach(() => {
  mockService = {
    isLoading: isLoadingSignal,
    data: dataSignal,
    fetchData: vi.fn(),
  };

  TestBed.configureTestingModule({
    providers: [
      {provide: DataService, useValue: mockService},
    ],
  });
});
```

---

## Mocking Okta Auth

```typescript
import {OKTA_AUTH} from '@okta/okta-angular';

const mockOktaAuth = {
  getIdToken: vi.fn().mockReturnValue('fake-token'),
  isAuthenticated: vi.fn().mockResolvedValue(true),
  signInWithRedirect: vi.fn(),
  signOut: vi.fn(),
};

TestBed.configureTestingModule({
  providers: [
    {provide: OKTA_AUTH, useValue: mockOktaAuth},
  ],
});
```

---

## Mocking Router

```typescript
import {Router, ActivatedRoute} from '@angular/router';

const mockRouter = {
  navigate: vi.fn(),
  navigateByUrl: vi.fn(),
  events: of(),
};

const mockActivatedRoute = {
  params: of({id: '123'}),
  queryParams: of({filter: 'active'}),
  snapshot: {
    params: {id: '123'},
    queryParams: {filter: 'active'},
  },
};

// For child routes: must provide both paramMap and parent.paramMap
// when component accesses route params from both locations
import {convertToParamMap} from '@angular/router';

const mockActivatedRouteWithParent = {
  paramMap: of(convertToParamMap({})),
  parent: { paramMap: of(convertToParamMap({id: 'REQ-1'})) },
  snapshot: { queryParamMap: convertToParamMap({}) },
};

TestBed.configureTestingModule({
  providers: [
    {provide: Router, useValue: mockRouter},
    {provide: ActivatedRoute, useValue: mockActivatedRoute},
  ],
});
```

---

## Signal-Based Route Mocking (Angular 21+)

For components using route signals, mock with `signal()`:

```typescript
const mockActivatedRoute = {
  // Signal-based params (Angular 21+)
  paramSignal: signal({id: '123'}),
  queryParamSignal: signal({filter: 'active'}),
  
  // Observable fallback for older code
  params: of({id: '123'}),
  queryParams: of({filter: 'active'}),
};
```

---

## Mocking Window/Document

```typescript
// Create mock window
const mockWindow = {
  innerWidth: 1024,
  innerHeight: 768,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
};

// Provide via injection token
import {DOCUMENT} from '@angular/common';

TestBed.configureTestingModule({
  providers: [
    {provide: 'Window', useValue: mockWindow},
  ],
});
```

---

## Service Mocks - Signals vs Observables

For services that expose signals:
```typescript
const mockService = {
  // Signal-based state
  data: signal<Data[]>([]),
  isLoading: signal(false),
  error: signal<Error | null>(null),
  
  // Methods that modify signals
  load: vi.fn(() => mockService.data.set([...])),
};
```

For services that return Observables (HTTP):
```typescript
const mockHttpService = {
  getData: vi.fn().mockReturnValue(of({...})),
};
```

> **When to use which mock pattern:**
> - Use `signal()` mocks for component state services
> - Use `of()` mocks for HTTP/data-fetching services
> - Use computed signals for derived state

---

## Vitest Mock Functions

```typescript
// Create mock function
const mockFn = vi.fn();

// Mock with return value
const mockWithReturn = vi.fn().mockReturnValue('value');

// Mock with resolved promise
const mockAsync = vi.fn().mockResolvedValue({data: 'async'});

// Mock with rejected promise
const mockRejected = vi.fn().mockRejectedValue(new Error('Failed'));

// Mock implementation
const mockImpl = vi.fn().mockImplementation((arg) => arg * 2);

// Verify calls
expect(mockFn).toHaveBeenCalled();
expect(mockFn).toHaveBeenCalledTimes(2);
expect(mockFn).toHaveBeenCalledWith('arg1', 'arg2');

// Clear mocks
vi.clearAllMocks(); // Clears call history
vi.resetAllMocks(); // Clears history and implementations
```

---

## Mocking Modules

```typescript
// Mock entire module
vi.mock('@core/services/analytics.service', () => ({
  AnalyticsService: vi.fn().mockImplementation(() => ({
    track: vi.fn(),
    identify: vi.fn(),
  })),
}));

// Mock specific exports
vi.mock('@core/utils/helpers', async () => {
  const actual = await vi.importActual('@core/utils/helpers');
  return {
    ...actual,
    formatDate: vi.fn().mockReturnValue('2024-01-01'),
  };
});
```

---

## Partial Mocks with MockedObject

```typescript
import {MockedObject} from 'vitest';

// Partial mock - only mock what you need
let mockService: MockedObject<Partial<ComplexService>>;

mockService = {
  // Only mock the methods/properties used in tests
  data: signal([]),
  isReady: signal(true),
};

// Full mock with all properties
let fullMockService: MockedObject<ComplexService>;
```

---

## Spy on Existing Methods

```typescript
// Spy on service method
const service = TestBed.inject(MyService);
const spy = vi.spyOn(service, 'doSomething');

// Call the method
service.doSomething('arg');

// Verify
expect(spy).toHaveBeenCalledWith('arg');

// Restore original
spy.mockRestore();
```
