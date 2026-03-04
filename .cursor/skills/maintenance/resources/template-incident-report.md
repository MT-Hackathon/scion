# Incident Report Template

Copy this template when documenting a production incident. Fill in all fields; leave no section blank.

```markdown
## Incident Report: [Brief Description]
**Severity**: P1/P2/P3
**Date**: YYYY-MM-DD HH:MM UTC
**Duration**: X hours Y minutes
**Impact**: [Who was affected and how]

### Timeline
- HH:MM - Issue detected by [monitoring/user report]
- HH:MM - Investigation started
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Service restored

### Root Cause
[What caused the issue]

### Resolution
[What was done to fix it]

### Prevention
[What will be done to prevent recurrence]
- [ ] Action item 1
- [ ] Action item 2
```

## Severity Guide

| Level | Definition | Response Time |
|-------|-----------|---------------|
| P1 | Complete outage, data loss risk | Immediate |
| P2 | Major feature broken, significant user impact | < 1 hour |
| P3 | Minor degradation, workaround available | Next business day |
