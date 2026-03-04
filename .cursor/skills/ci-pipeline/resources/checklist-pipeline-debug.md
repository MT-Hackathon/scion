# Pipeline Debugging Checklist

Follow this sequence for consistent CI/CD incident triage.

## 0) Select Provider Context
Use the provider that matches the GitLab instance you are debugging.

```bash
# Examples:
--provider gitlab   # GitLab.com
--provider state    # Other configured GitLab instance
```

## 1) Identify Failed Pipeline
```bash
uv run .cursor/skills/git-workflows/scripts/git-pipeline.py list --provider gitlab --status failed --limit 5
```

## 2) Get Jobs for the Pipeline
```bash
uv run .cursor/skills/git-workflows/scripts/git-pipeline.py jobs <pipeline_id> --provider gitlab
```

## 3) Find the Failed Job
- Locate jobs with `status=failed`.
- Record `job_id`, stage, and failure reason.

## 4) Pull Job Trace
```bash
uv run .cursor/skills/git-workflows/scripts/git-pipeline.py trace <job_id> --provider gitlab --tail 300
```

## 5) Diagnose
- Map the failure to a bucket: test, build, deploy, trigger/downstream, or infrastructure.
- Confirm whether failure is reproducible or flaky.

## 6) Act
- Retry failed pipeline:
```bash
uv run .cursor/skills/git-workflows/scripts/git-pipeline.py retry <pipeline_id> --provider gitlab
```
- Cancel stale run:
```bash
uv run .cursor/skills/git-workflows/scripts/git-pipeline.py cancel <pipeline_id> --provider gitlab
```
- Trigger a clean rerun on target ref:
```bash
uv run .cursor/skills/git-workflows/scripts/git-pipeline.py trigger --provider gitlab --ref main
```
- If trace shows code/config defect, fix and push with smallest safe change.
