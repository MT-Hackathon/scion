# Reference: Consolidation Patterns

Heuristics for when to create, merge, or split rules.

---

## Redundancy Detection Workflow

### Step 1: Search First

```bash
ls .cursor/rules/
grep -r "your-topic" .cursor/rules/*/RULE.mdc
```

### Step 2: Calculate Overlap

```
Overlap = Shared concepts / Total unique concepts
```

### Step 3: Apply Decision Criteria

| Overlap | Action |
|---------|--------|
| **≥80%** | UPDATE existing rule (never create new) |
| **40-80%** | EVALUATE if different aspect justifies new rule |
| **<40%** | CREATE new rule |

---

## Example: RBAC Rule Creation

### Search First

```bash
grep -r "authorization\|permissions\|roles" .cursor/rules/
```

Found: `105-security` (related but different focus)

### Overlap Calculation

- Shared: auth concepts (20%)
- Unique: RBAC-specific patterns (80%)

### Decision

Overlap < 40% → Create `267-rbac-authorization/`

---

## Consolidation Heuristics

**Split when:**

- "Use when / DO NOT use" criteria are genuinely different
- Content would require different activation contexts

**Merge when:**

- Rules would duplicate context to be self-contained
- Heavy cross-referencing between rules (red flag)

**Cost awareness:**

- Each rule adds ~30 tokens of description to system prompt
- Fewer, well-scoped rules beat many fragmented rules

---

## Token Discipline

| Component | Budget | Purpose |
|-----------|--------|---------|
| `description` field | 30-50t | Activation keywords + negations |
| Core rule content | 150-300t | Key mandates only |
| Resources | On-demand | Details loaded when needed |

**Lazy loading principle:** Resources are loaded only when the model needs them. Put details in resources, not the main rule.

**Script documentation:** Rule content (not description) should list key scripts with one-line purpose.

---

## Resource Naming Convention

### Why Descriptive Names Matter

Generic names like `patterns.md` create monolithic files and lose progressive discovery at the filename level.

### Naming Pattern

```
{prefix}-{topic}.md
```

### Prefix Categories

| Prefix | Purpose | When to Use |
|--------|---------|-------------|
| `examples-` | Working code, usage patterns | Showing how to do something |
| `reference-` | Lookup tables, registries, specs | Data that gets consulted |
| `checklist-` | Validation steps, pre-flight | Before/after action gates |
| `guide-` | Procedural how-to, workflows | Step-by-step instructions |

### Good Examples

```
resources/
├── examples-search-first.md
├── reference-anchor-types.md
├── checklist-pre-change.md
└── guide-type-sync.md
```

### Bad Examples (Avoid)

```
resources/
├── patterns.md      # Too generic
├── checklist.md     # Which checklist?
├── misc.md          # Never use
```

### Constraints

- **One concept per file**: ~50-150 lines max
- **Filename is the summary**: Reader should know content from name alone

---

## Pattern/Project Implementation Convention

### When to Use

Use `## Pattern` and `## Project Implementation` sections when a resource contains both generalizable patterns AND project-specific implementations (file paths, store names, component references).

### Structure

```markdown
# [Topic] Patterns

## Pattern
[Generalizable approach - portable across projects]

## Project Implementation
[Project-specific: paths, stores, components, endpoints]
```

### When NOT to Use

Skip the split for:

- Pure reference content (lookup tables)
- Pure checklists (validation steps)
- Content that is entirely generalizable OR entirely project-specific

### Porting Workflow

To adapt rules for a new project:

```bash
grep -r "## Project Implementation" .cursor/rules/
```

This finds all sections that need updating for the new project.
