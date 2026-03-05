# Issue Curation Guide

Issue curation is the practice of maintaining a backlog where every open issue is a real, actionable signal — not noise, not a duplicate, not already fixed. A bloated backlog is as harmful as no backlog: it obscures priority, wastes triage time, and erodes trust in the issue tracker as a source of truth.

## When to Curate

- After a code review blitz that filed many issues quickly (automated reviewers miss context)
- Before sprint planning, to ensure prioritization is against real problems
- When the backlog exceeds ~30 open issues and has not been triaged recently
- When issues reference code that has since been changed or refactored

## Triage Categories

For each issue, assign one disposition:

| Disposition | When | Action |
|---|---|---|
| **close-implemented** | The described problem was fixed, the feature was built, or the work is complete | Close with comment citing the commit, branch, or session that addressed it |
| **close-duplicate** | Same problem filed more than once | Close the lower-quality or older duplicate; add a comment on the closed one linking to the surviving issue |
| **close-wontfix** | Out of scope, decided against, or the "problem" is intentional design | Close with an explanatory comment; move to a future epic if appropriate |
| **close-scaffolding-acknowledged** | Code is intentionally empty/dead as a placeholder for a future feature that is planned | Close the "delete this dead code" issue; add a comment documenting the scaffolding intent and what future issue tracks the implementation |
| **refine** | Real issue but incomplete: missing reproduction steps, no acceptance criteria, wrong labels, misleading title | Edit the issue body, update labels, add acceptance criteria; do not close |
| **keep-valid** | Real problem, well-described, appropriate priority | Leave open; verify labels and priority are correct |

## Quality Standard for a Well-Formed Issue

Every issue that remains open should have:

- **Title**: Describes the problem or outcome, not the implementation (`initSettings() swallows startup errors` not `add try/catch to initSettings`)
- **Body**: One of: (a) bug: steps to reproduce + expected vs actual, (b) feature/enhancement: user story or job-to-be-done + acceptance criteria, (c) refactor: what and why, with measurable definition of done
- **Labels**: `layer::backend|frontend|infra`, `type::bug|feature|enhancement|refactor|chore`, `priority::high|medium|low` (where known)
- **No duplicates**: Link or close duplicates before the issue is marked keep-valid

## Duplicate Detection Patterns

Common duplicate vectors in automated code reviews:

- The same bug filed separately from different angles: "X loses context" and "X should carry structured context" describe the same gap
- A bug filed during a review session and again during a previous session under a slightly different title
- A "dead code" issue filed by a reviewer who didn't see the scaffolding intent in adjacent comments

Strategy: before marking an issue keep-valid, search open issues for synonymous descriptions. Filter by the same `layer::` label and scan title and body for conceptual overlap.

## Intentional Scaffolding — Do Not Delete Issues Blindly

Some code that appears dead is intentional scaffolding for planned future features. Before filing or keeping a "delete this dead code" issue, check:

- Does the module have a comment explaining future intent?
- Is there a companion issue or epic that describes the feature it will support?
- Does the type/variant appear in documentation, a roadmap issue, or a planning document?

If the scaffolding is intentional and documented, the correct disposition is `close-scaffolding-acknowledged`, not "delete it." The closed issue should document what the scaffolding is for and link to the future implementation issue.

## Script Reference

All curation operations use the git-workflows skill scripts. Run from the repo root:

```bash
# List all open issues
uv run .cursor/skills/git-workflows/scripts/git-issue.py list --state open --limit 100 --project YOUR_GITLAB_PROJECT --provider gitlab

# Get a specific issue
uv run .cursor/skills/git-workflows/scripts/git-issue.py get <iid> --project YOUR_GITLAB_PROJECT --provider gitlab

# Close with comment
uv run .cursor/skills/git-workflows/scripts/git-issue.py update <iid> --state close --project YOUR_GITLAB_PROJECT --provider gitlab
uv run .cursor/skills/git-workflows/scripts/git-issue.py comment <iid> --body "REASON" --project YOUR_GITLAB_PROJECT --provider gitlab

# Update labels or title
uv run .cursor/skills/git-workflows/scripts/git-issue.py update <iid> --labels "add:priority::high,remove:priority::low" --project YOUR_GITLAB_PROJECT --provider gitlab
```

Replace `YOUR_GITLAB_PROJECT` with the `namespace/repo` slug for the project being curated. See the [git-workflows skill](../../git-workflows/SKILL.md) for full script documentation and GitHub provider support.
