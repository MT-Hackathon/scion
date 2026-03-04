# VPN Sync Workflow Checklist

Use this checklist when syncing to State GitLab (`git.mt.gov`).

## Remote Configuration

| Name | Destination | Purpose |
|------|-------------|---------|
| `origin` | CDO GitLab | Primary development remote |
| `github` | GitHub | Secondary backup/collaboration |
| `state` | State GitLab | Official State repository (VPN-only) |

## Sync Workflow

- [ ] **Verify local state**: `git status`
- [ ] **Sync primary remotes**: `uv run remote-sync.py push`
- [ ] **Connect to VPN**: Launch GlobalProtect and verify "Connected" status.
- [ ] **Push to State GitLab**: `git push state HEAD`
- [ ] **Verify State sync**: `uv run remote-sync.py status`

## State GitLab Actions

- [ ] **Access Repository**: Open `https://git.mt.gov` in browser.
- [ ] **Create Merge Request**: Target the appropriate branch (e.g., `demo/prototype`).
- [ ] **Assign Reviewers**: Follow State-specific review protocols.
- [ ] **Disconnect VPN**: Once the push and MR creation are complete.

## Troubleshooting

### VPN connected but can't reach git.mt.gov
- Verify VPN shows "Connected" status.
- Try accessing other State resources to confirm routing.
- Check if `git.mt.gov` is accessible in browser first.

### Authentication Failures
- Ensure your State GitLab credentials are up to date.
- Verify SSH keys are correctly configured for `git.mt.gov`.

### Merge Conflicts
- Resolve conflicts locally on your primary branch.
- Push resolved changes to `origin` first, then sync to `state`.
