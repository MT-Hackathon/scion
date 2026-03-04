# mr

The work is done. Time to ship. 

Have Author write the commit messages first — thorough, explaining the why not just the what. Then have Author draft the MR body: what changed, why, which issues it closes (you should validate this if you dont already know). Use "Closes #X" syntax in the body for any issues from the epic so they close automatically on merge.

Before creating the MR, determine the target branch:
1. Run `git remote show origin` or check existing remote branches — look for an integration branch (e.g., `dev`, `develop`, `dev/offline-sprint`, `staging`).
2. If none exists and all feature branches in origin target `main`, use `main` as the target.
3. If it's ambiguous, ask before proceeding.

Use git-mr.py to create the MR from the current branch to the resolved target. 

This assumes /build has run and the branch is clean — pipeline green, lint passing. If anything is still open, finish it first.

Do not actually merge the MR. Bugbot will do review rounds first.
