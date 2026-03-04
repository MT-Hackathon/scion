# Reference: Edge Validation

Edge validation rules and connection logic.

---

## Pattern

### Connection Rules

| From | To | Allowed | Reason |
|------|-----|---------|--------|
| Source | Any | Yes | Sources can connect to any downstream |
| Transform | Transform | Yes | Chained transformations |
| Transform | Target | Yes | Output to storage |
| Target | Any | No | Targets are endpoints |
| Any | Source | No | Sources have no inputs |

### Prohibited Patterns

- **Circular dependencies** - Node A → Node B → Node A
- **Self-loops** - Node A → Node A
- **Multiple sources to single input** - Node A, Node B → Node C (single input)

### Validation Timing

- **On-drop** - Validate immediately when edge is created
- **Pre-save** - Validate entire graph before saving

### Error Feedback

```typescript
// On invalid connection
{
  valid: false,
  edge: {
    style: { stroke: 'red', strokeDasharray: '5,5' }
  },
  message: 'Cannot connect: circular dependency detected'
}
```

### ELT Transform Constraints

**Allowed operations:**
- Column filter (select/exclude columns)
- Row filter (where clauses)
- Anonymization (masking, hashing)
- Type coercion (string → number, etc.)

**Prohibited operations:**
- Joins (use database for this)
- Aggregations (GROUP BY, COUNT, SUM)
- Pivot/Unpivot
- Complex expressions (UDFs, window functions)
- Multiple input sources to single transform

---

## Project Implementation

### Validation Implementation

Location (planned): `app/frontend/src/lib/utils/edgeValidation.ts`

```typescript
export function validateConnection(
  source: Node,
  target: Node,
  existingEdges: Edge[]
): ValidationResult {
  // Check prohibited patterns
  if (source.id === target.id) {
    return { valid: false, message: 'Self-loops not allowed' };
  }
  
  if (target.type === 'apiSource') {
    return { valid: false, message: 'Cannot connect to source nodes' };
  }
  
  if (source.type === 'databaseTarget') {
    return { valid: false, message: 'Target nodes cannot have outputs' };
  }
  
  // Check for circular dependencies
  if (wouldCreateCycle(source.id, target.id, existingEdges)) {
    return { valid: false, message: 'Circular dependency detected' };
  }
  
  return { valid: true };
}
```

### Canvas Event Handling

Location (planned): `app/frontend/src/lib/components/Canvas.svelte`

Edge deletion, handle glow, and selection feedback are implemented here. Always reference this file before implementing new interaction patterns.
