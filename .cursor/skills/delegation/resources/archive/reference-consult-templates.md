# Consultation Templates

Use these templates to engage with peers. Choose the mode based on task ambiguity and complexity.

## Execution Mode vs. Consultation Mode

| Mode | When to use | Framing |
| :--- | :--- | :--- |
| **Execution Mode** | Low ambiguity, mechanical tasks, well-defined patterns. | "The todo IS the prompt." Direct, precise instructions. |
| **Consultation Mode** | High ambiguity, architectural pivots, logic changes, uncertainty. | "The todo is the SEED." Invite dialogue, pushback, and questions. |

---

## The Architect (`deep-code`)
**Template**: Consult on todo #[id] from @[plan-path]. Handshake on the approach via `resume` before you begin implementation.

**Add context when**:
- Architectural constraints or required patterns must be followed.
- Touch points or files are already identified in plan.

**Skip context when**:
- Plan fully specifies steps and acceptance criteria.
- Standard patterns apply.

## The Executor (`quick-code`)
**Template**: Consult on todo #[id] from @[plan-path]. Focus on precise execution of the localized changes.

**Add context when**:
- Change must stay minimal or localized.
- Exact files or sections are identified.

**Skip context when**:
- Plan gives precise instructions.
- No special constraints.

## The Synthesizer (`the-author`)
**Template**: Consult on todo #[id] from @[plan-path]. Ensure the documentation bridges the gap between implementation and intent.

**Add context when**:
- Target audience or tone requirements are known.
- Required references or sections are mandated.

**Skip context when**:
- Plan already includes outline and scope.
- Standard doc format is acceptable.

## The Critic (`reviewer`)
**Template**: Consult on todo #[id] from @[plan-path]. I'm looking for a technical second opinion—challenge my assumptions.

**Add context when**:
- Specific risks or regressions need focus.
- Tests or areas must be validated.

**Skip context when**:
- Plan includes a review checklist.
- General review is sufficient.

## The Auditor (`critical-reviewer`)
**Template**: Consult on todo #[id] from @[plan-path]. This is high-stakes; provide an independent perspective on systemic risks.

**Add context when**:
- High-risk areas or security/perf concerns to target.
- Known past issues to re-check.

**Skip context when**:
- Plan already defines critical checks.
- No extra risk flags.

## The QA (`test-validator`)
**Template**: Consult on todo #[id] from @[plan-path]. Verify the implementation against the test plan and report any friction.

**Add context when**:
- Required tests or commands are specified.
- Areas most likely to break are known.

**Skip context when**:
- Plan specifies test plan and commands.
- No special test constraints.

## explore
**Template**: Consult on todo #[id] from @[plan-path] to gather necessary context.

**Add context when**:
- Search scope should be limited (directories, subsystems).
- Known relevant files or symbols exist.

**Skip context when**:
- Plan already specifies scope and questions.
- No constraints beyond finding info.
