# Cross-Repository Leadership

In a multi-repo workspace, governance and coordination rules apply across all repositories:

- **Unified Governance**: Rules in the canonical `.cursor/` repository govern the entire team's behavior across all connected repositories.
- **Repo Isolation**: One repository per task. Do not ask a specialist to switch repositories mid-task.
- **Path Qualification**: Prefix all paths with the repository name (e.g., `my-api/src/...`) to avoid ambiguity when multiple repos share file naming patterns.
- **Commit Strategy**: Create separate, verified commits for each repository. Never combine changes from multiple repositories into a single commit.
- **Working Directory**: Always specify the `working_directory` parameter in tool calls when switching between repositories.
