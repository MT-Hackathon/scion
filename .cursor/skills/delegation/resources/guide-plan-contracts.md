# Guide: Plan Contracts for Agent Dispatch

This guide explains how to structure implementation plans using "contracts." A contract-style section is self-contained and explicitly signals to the main agent that it should be routed to a specialist. By defining inputs, outputs, and success criteria within the plan itself, you eliminate the need for manual prompt crafting during dispatch.

## Contract Template

Use this format for any plan section intended for specialist execution.

```markdown
## [Section ID] [Title] <Contract: agent-type>

**Inputs**: [what this section needs from prior sections or specific files]
**Outputs**: [files/artifacts produced or modified]
**Success Criteria**: [verifiable conditions/tests that must pass]
**References**: [skills/rules/docs the specialist must follow]
```

## Examples

### 1. Angular Service Implementation

This contract is designed for `the-executor`.

```markdown
## PHASE-2 Implement ScopeService <Contract: the-executor>

**Inputs**: `src/app/features/scopes/scope.ts` (model definition)
**Outputs**: `src/app/features/scopes/scope.service.ts`
**Success Criteria**:
- Service provides `getScopes()` returning `Observable<Scope[]>`
- Uses `HttpClient` with appropriate error handling
- 100% unit test coverage in `scope.service.spec.ts`
**References**:
- [angular-http-reactive](../../angular-http-reactive/SKILL.md)
- [140-angular-foundation](../../../rules/140-angular-foundation/RULE.mdc)
```

### 2. Code Review Task

This contract is designed for `the-qa-tester`.

```markdown
## REVIEW-1 Validate ScopeService Implementation <Contract: the-qa-tester>

**Inputs**: `src/app/features/scopes/scope.service.ts`
**Outputs**: Review comments/approval
**Success Criteria**:
- Implementation matches Phase-2 requirements
- No linter errors or anti-patterns
- RxJS operators used correctly for retry logic
**References**:
- [130-constitution-typescript](../../../rules/130-constitution-typescript/RULE.mdc)
- [angular-http-reactive](../../angular-http-reactive/SKILL.md)
```

## Routing Note

The presence of the `<Contract: agent-type>` tag in the heading is a direct instruction for the main agent. When you see this format in a plan, you can dispatch the section directly to the specified agent without adding extra explanation. The contract itself provides all the necessary context for the specialist to work independently.
