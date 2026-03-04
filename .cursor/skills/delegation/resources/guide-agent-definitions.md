# Agent Definition Principles

This guide defines the structural requirements for `.cursor/agents/*.md` files.

## The Audience
Agent definitions are **system prompts for the agent**, not instructions for the orchestrator. The orchestrator uses the frontmatter `description` for routing; the body is the agent's operating manual.

## What Belongs
- **Identity & Disposition**: Who is this colleague? What is their "vibe" and decision-making style?
- **Expertise Scope**: What are they called for? What specific domains do they own?
- **Behavioral Invariants**: What do they *always* do, regardless of the task or project?
- **Self-Verification**: How do they confirm their work is correct before returning?
- **Handoff Protocol**: How do they deliver their results? (e.g., direct writes, structured JSON)

## What Does NOT Belong
- **"NOT Your Domain" / Routing**: This is orchestrator knowledge. The agent doesn't need to be told what other agents do.
- **Project-Specific Commands**: (CI, build, lint) — Agents read `rules/` and `skills/` for the current project's environment.
- **Language-Specific Patterns**: Keep the agent's core identity language-agnostic unless the agent's *purpose* is language-specific (e.g., a Python specialist).
- **Self-Sufficiency Restrictions**: Do not prevent agents from fixing issues they find within their domain.

## The Invariant/Variant Principle
- **Agent Definitions (Invariant)**: Teach the agent *how to be*. These are stable across projects.
- **Skills (Domain Knowledge)**: Teach the agent *what to know*.
- **Rules (Project Context)**: Teach the agent *where they are*.

When variant/project-specific content migrates into agent definitions, the system becomes brittle and requires manual updates for every new repo.

## The Briefing vs Methodology Test

When reviewing or writing agent body content, apply this test to each section:

> "If I briefed a different agent to do this work, would I need to copy this section into their brief?"

- If **yes** → it is domain knowledge and belongs in a skill.
- If **no** → it is identity, persona, tool assignment, or behavioral mandate, and belongs in the agent.

Examples of content that **fails** this test (methodology masquerading as identity):
- Step-by-step inspection protocols
- Output format templates
- Classification taxonomies and shared vocabularies
- Project-specific CI commands
- Orchestration flow diagrams ("Research → Implementation → Executor")

## Self-Sufficiency within Scope
Agents should fix issues they find within their domain rather than relaying problems through the orchestrator.
- **The Boundary is Purpose**: Why was this agent called? (e.g., Curation, QA, Implementation)
- **The Capability is Total**: Within that purpose, the agent has the authority and responsibility to be self-sufficient.

*Example*: If a Curator finds a bug in a curation script, it should fix the script directly. It does not need to report it back for an Executor to handle.

## Periodic Agent Health Audit

Run during curation cycles — when a new skill is created that covers an agent's domain, or at natural synthesis moments.

- Does the body contain methodology (checklists, protocols, output templates, taxonomies) that could serve another agent? → Extract to a skill.
- Does it contain project-specific commands or tooling that duplicate a skill? → Remove; point to the skill.
- Does it contain "NOT Your Domain" routing that tells the agent what other agents do? → Remove; the orchestrator handles routing.
- Does it contain orchestration flow diagrams? → Remove; these belong in the delegation skill.
- Is the body over ~80 lines? → Audit for methodology creep.
- Does it reference the skills that govern its domain knowledge? → Add skill references if missing.
