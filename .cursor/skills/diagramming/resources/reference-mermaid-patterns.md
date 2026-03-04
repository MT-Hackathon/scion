# Mermaid Patterns Reference

Quick-reference for the most commonly needed Mermaid syntax patterns.

## Flowchart

```
flowchart TD
    A[Rectangle] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[Other Action]
    C --> E([Rounded])
    D --> E
```

**Direction**: `TD` (top-down), `LR` (left-right), `BT` (bottom-top), `RL` (right-left).

**Shapes**: `[Rectangle]`, `{Diamond}`, `([Stadium])`, `[(Cylinder)]`, `[/Parallelogram/]`, `((Circle))`.

**Subgraphs**:
```
subgraph title [Display Label]
    Node1 --> Node2
end
```

## Sequence Diagram

```
sequenceDiagram
    actor User
    participant API as REST API
    participant DB as Database

    User->>API: POST /resource
    activate API
    API->>DB: INSERT
    DB-->>API: result
    API-->>User: 201 Created
    deactivate API
```

**Arrows**: `->>` solid, `-->>` dashed, `-x` cross (async), `-)` open arrow.

**Activation**: `activate`/`deactivate` or `+`/`-` suffix on arrows.

**Notes**: `Note over API,DB: Transactional boundary`

**Loops/Alt**:
```
alt success
    API-->>User: 200 OK
else error
    API-->>User: 500 Error
end

loop Retry 3 times
    API->>DB: query
end
```

## ER Diagram

```
erDiagram
    ENTITY_A {
        uuid id PK
        string name
        timestamp created_at
    }
    ENTITY_A ||--o{ ENTITY_B : "has many"
```

**Cardinality**: `||` exactly one, `o|` zero or one, `|{` one or more, `o{` zero or more.

**Attributes**: `type name [PK|FK|UK]`

## Class Diagram

```
classDiagram
    class ServiceA {
        -repository: Repository
        +process(dto: DTO) Result
        -validate(input: String) boolean
    }
    ServiceA --> Repository : uses
    ServiceA ..|> Interface : implements
```

**Visibility**: `+` public, `-` private, `#` protected, `~` package.

**Relations**: `-->` association, `..>` dependency, `..|>` implementation, `--|>` inheritance, `--o` aggregation, `--*` composition.

## State Diagram

```
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted : submit
    Submitted --> Approved : approve
    Submitted --> Rejected : reject
    Rejected --> Draft : revise
    Approved --> [*]
```

## Styling Tips

- **Node IDs**: No spaces. Use `camelCase` or `under_score`. Display text goes in brackets: `myNode["Display Text"]`.
- **Special characters in labels**: Wrap in double quotes: `A["Step 1: Init"]`.
- **Avoid**: HTML tags (`<br/>`), explicit colors/styles (breaks dark mode), `click` events, node IDs named `end` or `subgraph`.
- **Long labels**: Keep node labels short. Use edge labels for details: `A -->|"details here"| B`.
