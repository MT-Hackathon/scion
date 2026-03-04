# Examples: HTTP Testing

Patterns for testing HTTP calls and interceptors with Vitest and Angular.

> **Note on Subscription Patterns**: To comply with `rxjs-x/no-ignored-subscription`, avoid bare `.subscribe()` in tests. Prefer `firstValueFrom()` for a cleaner async/await flow, or provide an explicit error handler in the observer object.

---

## Testing HTTP Interceptors

```typescript
import {beforeEach, describe, expect, it} from 'vitest';
import {HttpClient, provideHttpClient, withInterceptors} from '@angular/common/http';
import {HttpTestingController, provideHttpClientTesting} from '@angular/common/http/testing';
import {TestBed} from '@angular/core/testing';
import {OKTA_AUTH} from '@okta/okta-angular';
import {tokenInterceptor} from './token-interceptor';

describe('tokenInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  const mockOktaAuth = {
    getIdToken: () => 'fake-id-token',
  } as unknown as any;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        {provide: OKTA_AUTH, useValue: mockOktaAuth},
        provideHttpClient(withInterceptors([tokenInterceptor])),
        provideHttpClientTesting(),
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('should add Authorization header with Bearer token', () => {
    http.get('/test').subscribe({
      error: (err) => fail(`Unexpected error: ${err}`),
    });

    const req = httpMock.expectOne('/test');
    expect(req.request.headers.get('Authorization')).toBe('Bearer fake-id-token');
    req.flush({ok: true});

    httpMock.verify();
  });
});
```

---

## Testing Service HTTP Calls

```typescript
import {HttpClient, provideHttpClient} from '@angular/common/http';
import {HttpTestingController, provideHttpClientTesting} from '@angular/common/http/testing';
import {TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {UserService} from './user.service';

describe('UserService', () => {
  let service: UserService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        UserService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(UserService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify(); // Verify no outstanding requests
  });

  it('should fetch user by id', async () => {
    const mockUser = {id: '123', name: 'John Doe'};

    const userPromise = firstValueFrom(service.getUser('123'));

    const req = httpMock.expectOne('/api/users/123');
    expect(req.request.method).toBe('GET');
    req.flush(mockUser);

    const user = await userPromise;
    expect(user).toEqual(mockUser);
  });

  it('should handle error response', async () => {
    const userPromise = firstValueFrom(service.getUser('invalid'));

    const req = httpMock.expectOne('/api/users/invalid');
    req.flush('Not found', {status: 404, statusText: 'Not Found'});

    try {
      await userPromise;
      fail('should have failed');
    } catch (error: any) {
      expect(error.status).toBe(404);
    }
  });
});
```

---

## Testing POST Requests

```typescript
it('should create user', async () => {
  const newUser = {name: 'Jane Doe', email: 'jane@example.com'};
  const createdUser = {id: '456', ...newUser};

  const userPromise = firstValueFrom(service.createUser(newUser));

  const req = httpMock.expectOne('/api/users');
  expect(req.request.method).toBe('POST');
  expect(req.request.body).toEqual(newUser);
  req.flush(createdUser);

  const user = await userPromise;
  expect(user).toEqual(createdUser);
});
```

---

## Testing Multiple Requests

```typescript
it('should fetch all users', async () => {
  const mockUsers = [
    {id: '1', name: 'User 1'},
    {id: '2', name: 'User 2'},
  ];

  const usersPromise = firstValueFrom(service.getAllUsers());

  const req = httpMock.expectOne('/api/users');
  req.flush(mockUsers);

  const users = await usersPromise;
  expect(users.length).toBe(2);
});

it('should handle parallel requests', () => {
  service.getUser('1').subscribe({
    error: (err) => fail(`Unexpected error: ${err}`),
  });
  service.getUser('2').subscribe({
    error: (err) => fail(`Unexpected error: ${err}`),
  });

  const requests = httpMock.match('/api/users/');
  expect(requests.length).toBe(2);

  requests[0].flush({id: '1', name: 'User 1'});
  requests[1].flush({id: '2', name: 'User 2'});
});
```

---

## Testing with Query Parameters

```typescript
it('should fetch users with filters', () => {
  service.searchUsers({role: 'admin', active: true}).subscribe({
    error: (err) => fail(`Unexpected error: ${err}`),
  });

  const req = httpMock.expectOne(
    req => req.url === '/api/users' &&
           req.params.get('role') === 'admin' &&
           req.params.get('active') === 'true'
  );
  expect(req.request.method).toBe('GET');
  req.flush([]);
});
```

---

## Testing Request Headers

```typescript
it('should include custom headers', () => {
  service.fetchWithCustomHeaders().subscribe({
    error: (err) => fail(`Unexpected error: ${err}`),
  });

  const req = httpMock.expectOne('/api/data');
  expect(req.request.headers.get('X-Custom-Header')).toBe('custom-value');
  expect(req.request.headers.get('Content-Type')).toBe('application/json');
  req.flush({});
});
```
