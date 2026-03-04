# Rootstock Web App Personas

These personas define the primary users of the Rootstock control plane. Visual QA agents should use these archetypes to ground their testing in human intent, ensuring the UI remains intuitive for both novices and experts.

---

## Alex — The New Contributor
**Archetype**: The Onboarding Developer

### Who are they?
Alex is a developer joining a team that uses Rootstock. They have been told to "connect their project to the graft engine" but have never used Rootstock before. They are comfortable with git but unfamiliar with Rootstock-specific terminology like "canonical," "drift," or "graft policy."

### What do they need?
- A friction-free onboarding path to connect their local project.
- Contextual help or clear labels that explain what is happening during the first sync.
- Immediate visual confirmation that their project is "safe" and "synced."

### Constraints
- High cognitive load (new project, new team, new tools).
- Impatient with "magic" that doesn't explain itself.
- Minimal domain vocabulary.

### Success looks like
Alex connects their first project in under 60 seconds and feels confident that their `.cursor` environment is now aligned with the team's standards.

### Frustration looks like
The "Connect Project" form asks for paths or configurations Alex doesn't understand, or the first sync fails with an error message that requires expert knowledge to debug.

---

## Sam — The Daily Practitioner
**Archetype**: The Workflow Optimizer

### Who are they?
Sam is an experienced developer who uses Rootstock daily across multiple projects. They contribute to the team's shared knowledge and rely on Rootstock to keep their environment sharp. They use the web app as a quick health-check dashboard.

### What do they need?
- A high-level overview of all connected projects.
- Fast identification of "drifted" projects that need attention.
- Quick-action buttons to pull updates or check status without deep navigation.
- Efficient access to settings and policy classifications.

### Constraints
- Time-constrained; they want to spend their focus on code, not tool management.
- Uses the app as a secondary "control panel" while their IDE is primary.

### Success looks like
Sam opens the dashboard, sees a project has drifted, clicks a single "Pull" button, and returns to their IDE within 15 seconds.

### Frustration looks like
Having to click through multiple levels of navigation to perform a simple sync check, or missing a critical drift indicator because it was buried in a row detail.

---

## Jordan — The Curator
**Archetype**: The System Architect

### Who are they?
Jordan is a senior developer or architect responsible for the quality of the team's shared AI knowledge. They review contributions from other developers and decide what becomes "canonical." They care about the structural integrity of the `.cursor` environment.

### What do they need?
- Oversight of sync health across the entire organization.
- Detailed diff views to review proposed changes to rules and skills.
- The ability to approve, reject, or batch-update knowledge artifacts.
- Control over global policies and file classifications.

### Constraints
- High responsibility; a bad rule change affects the entire team.
- Cares more about precision and quality than speed.

### Success looks like
Jordan reviews five proposed skill updates, identifies a potential conflict in one, rejects it with a comment, and approves the rest in a single session.

### Frustration looks like
Opaque sync logs that don't clearly show *what* changed, or a UI that makes it difficult to distinguish between local experiments and canonical improvements.
