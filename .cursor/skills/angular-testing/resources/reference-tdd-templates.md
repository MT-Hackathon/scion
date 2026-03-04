# TDD Test-First Templates

> Copy these templates to create failing tests BEFORE writing implementation. Replace placeholders (`{PLACEHOLDER}`) with your specific values.

> **Subscription Handling**: Use `firstValueFrom()` for cleaner async/await flow in tests. Always unsubscribe or use `take(1)` for output subscriptions.

## 1. HTTP Service Template

**Purpose**: Define the API contract before implementation.

**Test categories** (write first):
- API contract: method + URL + headers
- Request body structure
- Response mapping to domain model
- Error handling: 4xx, 5xx, network

```typescript
describe('{ServiceName}', () => {
  let service: {ServiceName};
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        {ServiceName},
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject({ServiceName});
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('sends {METHOD} to {ENDPOINT}', async () => {
    const call = firstValueFrom(service.{methodName}({payload}));

    const req = httpMock.expectOne('{ENDPOINT}');
    expect(req.request.method).toBe('{METHOD}');
    expect(req.request.body).toEqual({payload});
    req.flush({response});

    await call;
  });

  it('maps response to domain model', async () => {
    const call = firstValueFrom(service.{methodName}());

    httpMock.expectOne('{ENDPOINT}').flush({apiResponse});

    const result = await call;
    expect(result).toEqual({domainModel});
  });

  it('handles 4xx error', async () => {
    const call = firstValueFrom(service.{methodName}());

    httpMock.expectOne('{ENDPOINT}').flush(
      {errorBody},
      { status: 400, statusText: 'Bad Request' }
    );

    await expect(call).rejects.toMatchObject({ status: 400 });
  });

  it('handles 5xx error', async () => {
    const call = firstValueFrom(service.{methodName}());

    httpMock.expectOne('{ENDPOINT}').flush(
      {errorBody},
      { status: 500, statusText: 'Server Error' }
    );

    await expect(call).rejects.toMatchObject({ status: 500 });
  });

  it('handles network error', async () => {
    const call = firstValueFrom(service.{methodName}());

    httpMock.expectOne('{ENDPOINT}').error(
      new ProgressEvent('error'),
      { status: 0, statusText: 'Network Error' }
    );

    await expect(call).rejects.toMatchObject({ status: 0 });
  });
});
```

**What to defer**: Integration tests, retry logic, caching, UI error presentation.

---

## 2. State Service Template (Signal-Based)

**Purpose**: Define state shape, computed derivations, and effect behavior.

**Test categories** (write first):
- Initial state values
- Computed signal derivations
- Effect triggers and side effects

```typescript
describe('{StateService}', () => {
  let service: {StateService};
  let sourceSignal: WritableSignal<{Type}>;

  beforeEach(() => {
    sourceSignal = signal({initialValue});

    TestBed.configureTestingModule({
      providers: [
        {StateService},
        { provide: {SourceToken}, useValue: { sourceSignal } },
      ],
    });

    service = TestBed.inject({StateService});
  });

  it('starts with initial state', () => {
    expect(service.state()).toEqual({initialState});
  });

  it('derives {computedName} from source signals', () => {
    sourceSignal.set({newValue});
    TestBed.flushEffects();

    expect(service.{computedName}()).toEqual({expected});
  });

  it('triggers effect when {condition}', () => {
    const spy = vi.fn();
    // ... setup spy

    sourceSignal.set({triggerValue});
    TestBed.flushEffects();

    expect(spy).toHaveBeenCalledWith({expectedArgs});
  });
});
```

**What to defer**: Component integration, template rendering, persistence optimization.

---

## 3. Component Template (Behavioral)

**Purpose**: Specify component contracts without DOM structure.

**Test categories** (write first):
- Input contracts (what inputs, what happens)
- Output contracts (what events, when emitted)
- Form validation (if reactive forms)
- Computed signals

```typescript
describe('{ComponentName}', () => {
  let fixture: ComponentFixture<{ComponentName}>;
  let component: {ComponentName};

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [{ComponentName}],
    });
    fixture = TestBed.createComponent({ComponentName});
    component = fixture.componentInstance;
  });

  it('applies input {inputName} to state', () => {
    fixture.componentRef.setInput('{inputName}', {inputValue});
    fixture.detectChanges();

    expect(component.{stateSignal}()).toEqual({expected});
  });

  it('emits {outputName} when {action}', async () => {
    const spy = vi.fn();
    const subscription = component.{outputName}.subscribe(spy);

    component.{actionMethod}();
    expect(spy).toHaveBeenCalledWith({payload});
    subscription.unsubscribe();

    // Or use firstValueFrom for one-shot:
    // const emittedValue = await firstValueFrom(component.{outputName}.pipe(take(1)));
    // expect(emittedValue).toEqual({payload});
  });

  it('validates {fieldName} is required', () => {
    component.form.patchValue({ {fieldName}: '' });
    expect(component.form.get('{fieldName}')?.hasError('required')).toBe(true);
  });

  it('computes {derivedSignal} from sources', () => {
    component.{sourceSignal}.set({value});
    TestBed.flushEffects();

    expect(component.{derivedSignal}()).toEqual({expected});
  });
});
```

**What to defer**: DOM structure, CSS classes, Material wrappers, layout assertions.

---

## 4. Directive Template

**Purpose**: Define host element behavior and attribute binding.

**Test categories** (write first):
- Host element modifications
- Event handling
- Input-driven attribute changes

```typescript
@Component({
  template: `<div {directiveName} [{inputName}]="{value}"></div>`,
  imports: [{DirectiveName}],
})
class TestHostComponent {
  value = {initialValue};
}

describe('{DirectiveName}', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let hostEl: HTMLElement;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [TestHostComponent],
    });
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    hostEl = fixture.nativeElement.querySelector('[{directiveName}]');
  });

  it('adds {attribute} when {condition}', () => {
    fixture.componentInstance.value = {newValue};
    fixture.detectChanges();

    expect(hostEl.getAttribute('{attribute}')).toBe('{expected}');
  });

  it('handles {event} and triggers {effect}', () => {
    hostEl.dispatchEvent(new Event('{event}'));
    expect({sideEffect}).toBe(true);
  });
});
```

**What to defer**: Visual layout, complex DOM structure.

---

## 5. Guard/Interceptor Template

**Purpose**: Define route decisions and request transformation.

### Guard

```typescript
describe('{GuardName}', () => {
  let guard: {GuardName};
  let authMock: { isAuthenticated: Mock; hasRole: Mock };

  beforeEach(() => {
    authMock = { isAuthenticated: vi.fn(), hasRole: vi.fn() };

    TestBed.configureTestingModule({
      providers: [
        {GuardName},
        { provide: AuthService, useValue: authMock },
      ],
    });

    guard = TestBed.inject({GuardName});
  });

  it('allows authenticated and authorized users', () => {
    authMock.isAuthenticated.mockReturnValue(true);
    authMock.hasRole.mockReturnValue(true);

    expect(guard.canActivate({route}, {state})).toBe(true);
  });

  it('redirects unauthenticated users', () => {
    authMock.isAuthenticated.mockReturnValue(false);

    const result = guard.canActivate({route}, {state});
    expect(result).toEqual({urlTreeOrFalse});
  });
});
```

### Interceptor

```typescript
describe('{InterceptorName}', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([{interceptorFn}])),
        provideHttpClientTesting(),
      ],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('adds {header} to requests', async () => {
    const call = firstValueFrom(TestBed.inject(HttpClient).get('{endpoint}'));

    const req = httpMock.expectOne('{endpoint}');
    expect(req.request.headers.get('{header}')).toBe('{value}');
    req.flush({});

    await call;
  });

  it('handles 401 by {action}', () => {
    // trigger request and flush 401, assert logout/redirect
  });
});
```

**What to defer**: End-to-end flows, UI feedback for denied routes.

---

## TDD Workflow Reminder

1. **Copy template** for your component type
2. **Replace placeholders** with your specific values
3. **Run test** - it should fail (red)
4. **Create minimal stub** to compile
5. **Run test** - still fails (for right reason)
6. **Implement** - make test pass (green)
7. **Refactor** - clean up while staying green
8. **Add edge cases** - repeat cycle
