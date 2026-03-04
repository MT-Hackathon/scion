# Examples: Terminal Commands

Terminal command patterns for procurement-web development.

---

## Angular Development

```bash
# Start Development Server
npm start

# Run Tests
npm test

# Generate Component
ng generate component features/my-feature
```

## Rule Script Commands

```bash
# Run GitLab Scripts
uv run .cursor/skills/git-workflows/scripts/fetch_project.py

# Run Validation Scripts
uv run .cursor/skills/rule-authoring-patterns/scripts/validate-frontmatter.py

# Run Conversation History Scripts
uv run .cursor/skills/conversation-history/scripts/check-last-chat.py
```

## Command Chaining

Always use `&&` for error propagation to ensure subsequent commands only run if previous ones succeed.

```bash
# Correct: Stops if any command fails
npm install && npm start
```

## Path Handling

Always quote paths that contain spaces to prevent shell parsing errors.

```bash
# Correct
cd "C:\Users\cmb115\projects\procurement-web"
```

## Troubleshooting

```bash
# Clear Node Modules (Windows PowerShell)
Remove-Item -Recurse -Force node_modules, package-lock.json; npm install

# Verify uv Installation
uv --version
uv python list
```
