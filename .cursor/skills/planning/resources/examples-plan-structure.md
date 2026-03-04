# Examples: Plan Structure

Planning workflow, todo conventions, and test pattern examples.

---

## Agent-Dispatchable Todos

### Convention Format

```
[agent] files: action → return
```

### Good Todo Examples

```yaml
todos:
  # Single-file quick edits
  - id: slim-executor
    content: "[the-executor] .cursor/agents/executor.md: Remove lines 28-74, add skill refs to delegation and testing-debugging → confirmation"
    status: pending
    
  # Documentation tasks  
  - id: extract-communication
    content: "[the-author] delegation/SKILL.md: Extract Agent Communication section to resources/guide-agent-communication.md → confirmation"
    status: pending
    
  # Multi-file implementation
  - id: refactor-auth-flow
    content: "[the-executor] auth.service.ts, auth.guard.ts, auth.interceptor.ts: Add token refresh with retry logic → summary of changes"
    status: pending
    
  # Review tasks
  - id: validate-changes
    content: "[the-qa-tester] .cursor/agents/*.md: Check persona focus, skill refs present, no procedural bloat → issues list"
    status: pending
```

### Bad Todo Examples

```yaml
# Too vague - no agent, no files, no return constraint
- id: fix-auth
  content: "Fix the authentication issues"
  status: pending

# Missing return constraint - agent will be verbose  
- id: update-docs
  content: "[the-author] README.md: Update installation instructions"
  status: pending

# Wrong agent for scope - the-architect doesn't write code
- id: refactor-services
  content: "[the-architect] services/*.ts: Refactor all services to use signals"
  status: pending
```

---

## Planning Workflow

### Step 1: Prerequisite Checks
Before planning work that touches:

- **Authentication/Okta**: Verify Okta config in `src/environments/environment.ts`
- **Services**: Search `src/app/core/services/` for existing services
- **Git/GitLab/GitHub APIs**: Check scripts in `.cursor/skills/git-workflows/scripts/`
- **Tests**: Confirm `nvm use 22` and `npm install` complete

### Step 2: Structure Plan
**Steps** (3-5 per feature):

- File path + function name + line range
- Before/after code structure
- Specific directives

### Step 3: Define Tests
For each code change:

- State delta verification
- Guard clause tests with invalid inputs
- null/undefined/boundary tests

---

## Good Plan Example

```markdown
## Step 1: Add validation to service
File: `src/app/core/services/user.service.ts:45-67`

Before:
validateUser(data: unknown): boolean {
  return true;
}

After:
validateUser(data: unknown): boolean {
  if (!data) {
    throw new Error('Data required');
  }
  if (!this.isUser(data)) {
    throw new Error('Invalid user data');
  }
  return true;
}

Verification: `npm test -- user.service`

Test Coverage:
- Valid user data returns true
- null data throws Error
- Invalid structure throws Error
```

## Bad Plan Example

```markdown
## Step 1: Fix validation
Update the validator to handle edge cases.

Test: Make sure it works.
```

**Problems**:

- No file path or line range
- No before/after code
- Vague language ("handle edge cases")
- No specific test criteria

---

## Test Quality

For patterns to avoid (tautological tests, type-only checks, magic numbers), refer to the **Anti-Patterns to Flag** section in [checklist-test-quality.md](../../angular-testing/resources/checklist-test-quality.md).
