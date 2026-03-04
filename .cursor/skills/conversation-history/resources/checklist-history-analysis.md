# Checklist: Conversation History

Pre-invocation validation for conversation history scripts.

---

## Pre-Invocation Checklist

### Database Availability

- [ ] Cursor database exists at expected location
- [ ] `CURSOR_DB_PATH` environment variable set (if non-standard location)
- [ ] Database file is readable (not locked by Cursor)

### Script Parameters

- [ ] Project path/name is correct (case-sensitive)
- [ ] File patterns use valid wildcard syntax (`*`, `?`)
- [ ] Search terms are specific enough (avoid single-word queries)
- [ ] Date ranges are reasonable (avoid excessive history scans)

### Context Integration

- [ ] Output will be used in plan or documentation (not just curiosity)
- [ ] Results will inform specific decision or implementation
- [ ] Script choice matches need (recent vs. search vs. trace)

## Script Selection Checklist

Choose the right script:

- [ ] **check-last-chat.py**: Need most recent N conversations
- [ ] **trace-file-discussions.py**: Need all mentions of specific file(s)
- [ ] **find-solution-patterns.py**: Need text search across conversations
- [ ] **analyze-failure-patterns.py**: Need failure mode analysis
- [ ] **export-project-knowledge.py**: Need full project knowledge dump
- [ ] **extract-code-solutions.py**: Need code snippets from past sessions

## Output Validation Checklist

After running script:

- [ ] Results are relevant to current task
- [ ] Timestamps indicate results are recent enough to be applicable
- [ ] File paths in results still exist in codebase
- [ ] Code snippets reflect current architecture (not obsolete)

## Integration Checklist

When incorporating results:

- [ ] Add findings to plan rationale section
- [ ] Update cross-references if patterns identified
- [ ] Create rule/skill if recurring pattern found
- [ ] Note any deprecated approaches to avoid
