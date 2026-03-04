# Pre-Implementation Checklist

Use this before writing implementation code. It is a quick way to route work to the right specialist and stay efficient.

---

## Delegation Decision Check

Before implementing, answer each question. If any answer is "Yes", delegation usually works better.

### Task Scope

- [ ] **3+ Steps?** Does this task require 3 or more distinct implementation steps?
  - Yes → Dispatch to `deep-code` or `quick-code`
  - No → May proceed directly

- [ ] **50+ Lines?** Will this change involve writing 50 or more lines of code?
  - Yes → Dispatch to `deep-code`
  - No → May proceed directly or use `quick-code`

- [ ] **Multi-File?** Does this span 2 or more independent files?
  - Yes → Dispatch in parallel to multiple agents
  - No → Single agent or direct handling

### Context Gathering

- [ ] **Research Needed?** Do I need to understand multiple subsystems before planning?
  - Yes → Use `explore` agent first
  - No → May proceed with direct reading

- [ ] **New Pattern?** Am I establishing a new architectural pattern or using an unfamiliar library?
  - Yes → Use **Research-Before-Implementation** (Pattern 5): parallel research → synthesis handoff.
  - No → May proceed with known patterns.

- [ ] **5+ Files to Read?** Am I about to read 5 or more files for context?
  - Yes → Use `explore` agent instead
  - No → May proceed with direct reading

### Task Type

- [ ] **Documentation?** Is this task writing documentation, docstrings, or markdown?
  - Yes → Dispatch to `the-author`
  - No → Use code agents

- [ ] **Review Needed?** Have I just completed implementation that needs validation?
  - Yes → Dispatch to `reviewer` before proceeding
  - No → Continue (but remember to validate before commit)

---

## Anti-Pattern Recognition

If you notice any of these, delegation tends to save time:

| What You're Doing | What You Should Do |
|-------------------|---------------------|
| Writing 50+ lines of code directly | Dispatch to `deep-code` |
| Reading 5+ files for context | Use `explore` agent |
| Re-writing plan content into specialist prompt | Dispatch the todo directly |
| Working on files one-by-one sequentially | Use parallel dispatch |
| Implementing without prior review of plan | Dispatch to `reviewer` first |
| Writing markdown/docs directly | Dispatch to `the-author` |

---

## Parallel Dispatch Opportunities

Check for parallelization before starting sequential work:

- [ ] **Independent Domains?** Can the work be split into independent problem domains?
- [ ] **Non-Overlapping Files?** Do the file sets not overlap between tasks?
- [ ] **No Dependencies?** Does no task depend on another's output?

If all three are true → Dispatch multiple agents simultaneously.

---

## Quick Reference

| Need | Agent | Condition |
|------|-------|-----------|
| Understand codebase | `explore` | Before planning, or 5+ files needed |
| Small code change | `quick-code` | Single file, ≤50 lines |
| Complex code change | `deep-code` | Multi-file or >50 lines |
| Documentation | `the-author` | Any markdown, docstrings, or docs |
| Spec compliance | `reviewer` | After implementation |
| Test validation | `test-validator` | After reviewer approves |

---

## Verification Protocol

After implementation, this sequence works well:

1. [ ] Dispatch `reviewer` for spec compliance
2. [ ] Fix any issues identified
3. [ ] Dispatch `test-validator` for test/lint validation
4. [ ] Then proceed to commit
