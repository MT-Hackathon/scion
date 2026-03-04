# Reference: Naming Conventions

Naming patterns across languages.

---

## Variable Naming

```python
# BAD: Abbreviated
req = get_request()
cfg = load_config()
t = time.time()

# GOOD: Descriptive
request = get_request()
config = load_config()
timeout_seconds = 30
current_timestamp = time.time()
```

## Function Naming

```python
# BAD: Vague or abbreviated
def proc():
    pass

def validate():
    pass

# GOOD: Action verb + object
def process_user_data():
    pass

def validate_authentication_config():
    pass

def calculate_backoff_duration():
    pass

# GOOD: ECS system suffix
def process_error_recovery_system(entity_store: pl.DataFrame) -> pl.DataFrame:
    pass
```

## Component Naming

```python
# BAD: Abbreviated
@dataclass(frozen=True)
class AuthCfg:
    pass

# GOOD: Descriptive + "Component"
@dataclass(frozen=True)
class AuthenticationConfigComponent:
    api_key_ref: str
    base_url: str
```

## Boolean Naming

```python
# BAD: Ambiguous
active = True
valid = False

# GOOD: Predicate prefix
is_active = True
has_valid_token = False
requires_authentication = True
```

## Constant Naming

```python
# BAD: Mixed case
MaxRetries = 3
timeoutSeconds = 30

# GOOD: UPPER_SNAKE_CASE
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
DEFAULT_BATCH_SIZE = 100
```

## TypeScript/Svelte Naming

```typescript
// BAD: Abbreviated
let cfg = $state({});
function proc() {}

// GOOD: Descriptive
let config = $state({});
function processUserInput() {}

// GOOD: Boolean predicates
let isLoading = $state(false);
let hasErrors = $state(false);
```
