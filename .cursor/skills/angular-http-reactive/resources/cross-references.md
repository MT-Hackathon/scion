# Cross-References

Related skills and documentation for HTTP and reactive patterns in Angular.

---

## Related Skills

### [Security Skill](../security/SKILL.md)
Contains critical patterns for:

- Token-based authentication interceptors
- Securing HTTP headers
- Handling 401 Unauthorized responses globally
- CSRF protection for POST/PUT requests

### [Angular Testing Skill](../angular-testing/SKILL.md)
Detailed guides for:

- Mocking HTTP requests with `HttpTestingController`
- Testing RxJS streams and timing with `fakeAsync` and `tick`
- Unit testing services that extend `BaseApiService`
- Integration testing components with HTTP dependencies

### [Angular Forms Material Skill](../angular-forms-material/SKILL.md)
Patterns for:

- Connecting form state to HTTP requests
- Handling validation errors returned from the API
- Preventing double-submits with `exhaustMap` during form submission
- Loading spinners and disabled states during API calls

---

## Shared Utilities

These utilities live in the consuming Angular project's `core/utils/` module (not in this repo):

- **ErrorExtractorService**: Standardized error message extraction from HTTP and application errors.
- **idempotentLoad**: Cache-aware loading with in-flight request deduplication.
- **runCrudMutation**: Standardized success/error handling for CRUD operations.

---

## External Resources

- [Angular HttpClient Documentation](https://angular.dev/guide/http)
- [RxJS Decision Tree](https://rxjs.dev/operator-decision-tree)
- [Learn RxJS - Operators by Category](https://www.learnrxjs.io/learn-rxjs/operators)
- [Angular Signals Documentation](https://angular.dev/guide/signals)
