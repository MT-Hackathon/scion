# Rootstock Mental Model

Rootstock is the knowledge curation and propagation system for shared AI
knowledge environments—primarily `.cursor` and `.claude`. It ensures that
hard-won collaboration insights—delegation patterns, testing philosophy,
error architecture, and specialized skills—are not lost to individual developer
silos but are integrated into a canonical baseline distributed to all connected
projects.

## 1. System Purpose
Rootstock solves the problem of **knowledge convergence**. In a multi-developer,
multi-project ecosystem, AI-human dyads generate unique learnings through
"hand-to-hand" combat with specific technical challenges. Claude Code uses
`.claude/` and Cursor uses `.cursor/` to store these insights, but the knowledge
remains the same across IDE surfaces. Without Rootstock, these learnings
evaporate when a session ends or a project is closed. Rootstock provides the
infrastructure to:

- **Integrate**: Pull diverse learnings from experimental project branches into
  a shared, neutral space.
- **Consolidate**: Identify overlapping patterns across different dyads and
  merge them into single, authoritative "NASA-grade" instructions.
- **Evaluate**: Apply a rigorous quality rubric to ensure only high-signal,
  low-noise knowledge enters the canonical environment.
- **Reorganize**: Maintain the structural integrity of the knowledge environment,
  ensuring that rules and skills are placed where they are most discoverable
  and effective.
- **Prune**: Actively remove stale, redundant, or low-value instructions to
  protect the "token budget"—the finite context window shared by the AI and
  human partner.

The ultimate goal is to move from **accumulation** (more rules) to **synthesis**
(better rules). Every instruction in the canonical environment must "earn its
place" by demonstrably changing how the AI behaves in future sessions.

## 2. The Curation Lifecycle
The lifecycle is a gated pipeline designed to filter local "hacks" into universal
"patterns." It moves knowledge through six distinct stages of increasing
authority:

1.  **push**: A **Contributor** copies their active local `.cursor` environment
    into a dedicated contributor branch in the Rootstock repository. This is an
    "as-is" snapshot of a working environment, capturing the "live" state of
    collaboration.
2.  **diff**: The system computes a classified delta. It distinguishes between
    structural changes (new rules/skills) and behavioral noise (transient
    session logs). This stage filters out 80% of the volume by identifying what
    is actually "new knowledge."
3.  **curate**: A specialized **Curator** agent analyzes the diff against the
    Rootstock quality rubric. It produces a structured report recommending
    whether to `merge`, `reject`, `reorganize`, or `prune` each change. The
    curator looks for resonance, clarity, and integration with existing rules.
4.  **review**: The human partner (the ultimate authority) reviews the curator's
    report. This stage resolves "flavor" decisions or complex architectural
    trade-offs that require human intuition. It is the final quality gate before
    a pattern becomes "canonical."
5.  **apply**: Approved changes are committed to the canonical `main` branch.
    This update triggers a version increment in the canonical state and updates
    the "Golden Image" shared by the network.
6.  **rebase**: Existing contributor branches are rebased onto the new `main`.
    This ensures that every new contribution is evaluated against the most
    current baseline, preventing "knowledge collisions" and ensuring that
    improvements are cumulative.

## 3. Distribution (Graft)
Graft is the "pull" half of the system. It is the engine that distributes the
curated canonical state to every connected project, ensuring that the entire
network benefits from the latest learnings.

- **Authority Strategy**: **Canonical wins on pull.** Because markdown-based
  knowledge artifacts (rules and skills) do not merge well using traditional
  3-way git logic, Rootstock enforces a "source of truth" model. To keep a local
  improvement, it must be pushed and curated into canonical; otherwise, a
  `graft pull` will overwrite it. This "forced alignment" ensures that the
  network does not fragment into slightly-different, incompatible versions of
  the same knowledge.
- **The Three-File Config Model**:
    - `.graft.json`: The "Identity Card." Committed to the project repo. It
      contains the project's unique UUID, its name, and a dictionary of template
      variables used to customize canonical rules for the local context.
    - `.graft.user.json`: The "Local Map." Gitignored. It stores the filesystem
      path to the local Rootstock repo and the developer's contributor ID. This
      allows different developers to have different local folder structures while
      pointing to the same canonical source.
    - `.graft.state.json`: The "Journal." Gitignored. It tracks the last-synced
      commit hash and file-level checksums to detect "unauthorized" local drift.
      It acts as the high-water mark for synchronization.

### 3.1 Learning Onboarding (First Connect)
When a new user connects an existing project to Rootstock for the first time,
the system runs a bidirectional Learning cycle before normal steady-state sync.
The sequence is deliberate:

1.  **Detect**: Inventory all existing `.cursor/` content in the target project.
2.  **Relocate**: Move existing local content into the protected zone (`200+`).
    - Numbered rules are renumbered from `000-199` to `200+` (for example,
      `001-foo` becomes `201-foo`).
    - Unnumbered rules receive a `200-` prefix.
    - Rules already in `200+` remain in place.
    - Name conflicts preserve both artifacts by prefixing the relocated local
      version with `Local_`.
3.  **Pull**: Apply scion canonical into the now-empty portable range (`000-199`)
    so the environment is fully populated with current conventions.
4.  **Prompt**: Issue a contextualized curation prompt to the now-briefed AI.
    It audits relocated content against canonical, consolidates overlap, keeps
    truly project-specific knowledge in `200+`, and identifies novel knowledge
    worth upstream contribution.
5.  **Push**: Send novel contributions to the contributor branch for central
    curation.

This ordering solves the bootstrapping problem: curation happens only after the
AI has received canonical guidance, so it can judge local material against the
shared standard rather than from an unbriefed state. In effect, each install is
also an ingestion event: every new user can enrich scion as part of onboarding.
(Reference: Issue #70)

## 4. File Classification Model
Not all files in a `.cursor` environment have the same lifecycle. Rootstock
uses a policy-driven engine (`graft-policy.json`) to determine how each path is
treated during a sync:

- **overwrite**: The canonical file is the absolute authority. Local versions
  are completely replaced. This is used for "portable" skills and foundational
  rules (e.g., `.cursor/rules/001-foundational/RULE.mdc`). These files are the
  "DNA" of the system.
- **template**: Canonical provides the logic and structure, but the local
  project provides the data. Placeholders like `{{PROJECT_NAME}}` or
  `{{TECH_STACK}}` are injected during the pull, allowing a single canonical
  rule to adapt to multiple project contexts.
- **content_filter**: Specifically designed for "semi-portable" rules like 998
  (Self-Portrait) or 999 (Codebase Briefing). It synchronizes the rule's
  frontmatter and instructions (the "how") but preserves the local body
  content (the "what"—like the specific self-portrait or codebase briefing).
- **protect**: Files that are seeded by canonical but owned by the project.
  Once created, they are never overwritten. This is the home for
  project-specific rules (numbered 200+).
- **ignore**: Files that must never be touched or seen by Rootstock, such as
  `.env` files, local cache directories, or personal scratchpads. These are
  strictly excluded from the curation pipeline.

## 5. Trust Boundaries and Security
Rootstock is built on the **Fail Closed** principle. If the system encounters
an unclassified file or a sensitive path, it defaults to protection or
exclusion rather than exposure.

- **Tools Sync, Artifacts Don't**: The *mechanisms* of AI collaboration (the
  scripts inside `.cursor/skills/`) are synced globally because they represent
  shared capability. However, the *output* of those tools (logs, briefings,
  personal motifs) is restricted to the local project boundary. Capability is
  shared; data is private.
- **Secrets Never**: Security is an invariant. No script in the Rootstock
  pipeline is permitted to read or transmit files classified as `ignore`.
  Credentials and secrets are geographically isolated from the curation path.
  Rootstock has no knowledge of their existence.
- **The 998/999 Boundary**: This is the architectural seam between shared
  knowledge and personal/project data. The *logic* for how an AI should
  remember a human (Rule 998) is a shared insight; the *actual memory* of that
  human is a private artifact. This distinction prevents personal session data
  from leaking across project boundaries.

## 6. Roles in the Ecosystem
- **The Curator**: The "discernment engine." Usually an AI agent specialized in
  synthesis. It prioritizes integration over accumulation and protects the
  system from "token bloat." It acts as the guardian of the canonical state.
- **The Contributor**: The "scout." Any developer-AI dyad operating in a
  project. They discover new failure modes, invent new workflows, and "push"
  these evolutions back to the hub for evaluation.
- **The Consumer**: Any connected project. It consumes the canonical environment
  via `graft pull`. Most contributors are also consumers, creating a virtuous
  cycle of learning and distribution.

## 7. Architecture and Data Flow
Rootstock organizes knowledge along two axes: **Reachability** (When does it
fire?) and **Portability** (Where does it apply?). The flow of knowledge follows
a hub-and-spoke model where the **scion** repository acts as the central hub.

**The scion repo** (`git@gitlab.com:cdo-office/scion.git`, public mirror at `github.com/MT-Hackathon/scion`) is a dedicated knowledge-only repository. It contains only `.cursor/` content — rules, skills, agents, hooks — plus `graft-policy.json` and `.rootstockignore`. No application code. The rootstock app repo connects to scion as a spoke project, the same as any other project. `main` is the canonical golden image; contributor branches (`contributor/{contributor}/{project_id}`) hold unreviewed submissions.

The runtime core is Rust: both the desktop app (`src-tauri/`) and CLI (`crates/graft-cli/`) consume the shared `graft-core` crate (`crates/graft-core/`).

### 7.1 Master-Detail Layout Pattern (Desktop UI)
For master-detail screens, the frontend uses an explicit three-layer composition:

```text
AppShell (sidebar + content area)
  └─ MasterDetailLayout (horizontal split + responsive mode)
       ├─ master: ListPage (pure list: header, filters, table, pagination)
       └─ detail: DrawerPeek (pure panel: chrome, close, scroll)
```

This pattern exists to enforce layout ownership boundaries and avoid recurring
cross-framework regressions:

- One layout owner per axis, and one scroll owner per pane.
- The master side scrolls as one continuous unit (stats through pagination).
- The detail panel occupies full available height, without vertical sandwiching.
- Push versus overlay behavior is decided by container width (container query),
  not viewport-wide breakpoints.
- Semantic components (`ListPage`) do not own viewport geometry; layout
  components (`MasterDetailLayout`) do.

The anti-pattern is stable and costly: when semantic components start owning
viewport geometry, master-detail bugs recur across implementations.
(Reference: `.cursor/plans/master-detail-layout.md`)

```mermaid
graph TD
    subgraph scion_hub [Scion Hub]
        direction TB
        F1["Foundational Rules (000-199)"]
        S1["Portable Skills"]
        A1["Agent Personas"]
        P0["graft-policy.json"]
    end

    subgraph spoke_rootstock [Rootstock App]
        R1["App code (Rust/SvelteKit)"]
        R2[".cursor/ (synced from scion)"]
    end

    subgraph spoke_project [Any Connected Project]
        P1["Project Context (998/999)"]
        P2["Local Rules (200+)"]
        P3[".cursor/ (synced from scion)"]
    end

    subgraph contributor [Contributor Branches]
        C1["contributor/adam_1/rootstock"]
        C2["contributor/adam_1/procurement"]
    end

    spoke_rootstock -- "graft push" --> contributor
    spoke_project -- "graft push" --> contributor
    scion_hub -- "graft pull" --> spoke_rootstock
    scion_hub -- "graft pull" --> spoke_project
    contributor -- "curation service (Phase B)" --> scion_hub
```

## 8. System States and Drift
| State | Behavior |
| :--- | :--- |
| **Canonical** | The "Golden Image" maintained in `rootstock/main`. It is the source of truth for the entire network. |
| **Contributor Branch** | A "Draft" state in the Rootstock repo where changes are curated but not yet authoritative. |
| **Connected Project** | A local repository linked to Rootstock via a `.graft.json` identity. |
| **Drifted (Inbound)** | The local project is behind; a newer canonical version is available. A `graft pull` is required. |
| **Drifted (Outbound)** | The local project has "un-pushed" knowledge that has not been curated. A `graft push` is recommended. |
| **Synced** | The local environment perfectly reflects the canonical intent. No changes are pending in either direction. |

## 9. The Four Surfaces of Engagement
Rootstock logic is encapsulated in the Rust `graft-core` crate and exposed
through four distinct interfaces.

1.  **The Desktop App (Tauri 2.0)**: The primary user-facing surface. It wraps
    the SvelteKit UI in an installable desktop shell, supports system tray
    workflows, and enables progressive disclosure from lightweight sync status
    to a full curation dashboard.
2.  **The CLI (`graft-cli`)**: The native Rust binary for power users and CI/CD
    pipelines. It is fast, scriptable, and built on the same `graft-core`
    logic as the desktop app for consistent policy enforcement and drift
    behavior.
3.  **The AI Skill**: The "Intelligence Layer." It allows any AI agent to reason
    about the curation lifecycle, execute `graft` commands, and self-correct
    when it detects that its environment is out of sync. It makes the system
    self-healing.
4.  **The MCP Server**: The same `rootstock` binary doubles as an MCP stdio
    server when invoked with `--mcp`. The MCP client (Cursor, Claude Desktop)
    spawns it as a child process — no port bound, no network exposure. It
    exposes 8 always-on gateway tools that progressively unlock to 23 via
    category discovery. This surface makes the ogham memory layer accessible
    mid-session (write, recall, capture, sync) rather than only at session
    boundaries. The tray app and MCP server are independent OS processes;
    each has its own lifetime. See [rootstock-mcp skill](../../../skills/rootstock-mcp/SKILL.md)
    for architecture, tool catalog, and client configuration.

## 10. Phased Architecture
The Rootstock system is designed to evolve in three distinct phases as it
transitions from a single-user tool to a collective intelligence platform.

### Phase A: Knowledge Convergence (Current)
- **State**: Local instances sharing the same git remote.
- **Identity**: Lightweight contributor identity (name string in `.graft.user.json`).
- **Curation**: Assisted by the Curator skill in Cursor.
- **Runtime**: Rust port in progress — desktop runtime is moving to Tauri 2.0,
  and the CLI is transitioning to a native Rust binary (`graft-cli`) rather
  than a Python script.
- **Support**: `.cursor` sync is operational; `.claude` support is planned.
- **Proactive Notification Queue**: `notifications` table in `graft_runtime.db` receives alerts from the running app (stale sync, scion advanced, health issues). The `sessionStart` hook delivers pending notifications by prepending them to the codebase briefing (Rule 999) and marks them delivered. Queue archives after 7 days. Zero overhead when queue is empty.

### Phase B: Centralized Curation (Near)
- **State**: Central hosted instance for multi-repo management.
- **Identity**: User accounts authenticated via git provider OAuth (GitHub/GitLab).
- **Curation**: Dedicated Curation Queue in the web UI.
- **Automation**: Autonomous scanning agent (using Opus via GitLab DUO or direct
  API) to proactively find and categorize new patterns.

### Phase C: Autonomous Evolution (Target)
- **State**: The AI maintains the canonical `main` branch autonomously.
- **Identity**: Enterprise integration (SCIM) for organizational scale.
- **Curation**: Full automation of the lifecycle; human review moves from
  "approval" to "audit."
- **Insight**: Real-time Knowledge Map visualization showing the evolution of
  patterns across the enterprise. The system self-evolves through collective dyad
  experience.

## 11. Canonical Environment Layout
The `.cursor/` or `.claude/` directory is the "brain" of the project. Rootstock
organizes it into clear functional zones:

- **rules/**:
    - `000-199 (Portable)`: Universal mandates (e.g., Foundational, NASA Power
      of 10). These represent the "constitution" of the system.
    - `200+ (Protected)`: Project-specific divergence. These are seeded by
      Rootstock but owned by the local dyad. They represent the "local laws."
    - `998-999 (Generated)`: Content-filtered rules for "working memory"
      (Temporal Self and Codebase Sense). Rootstock synchronizes the instruction
      structure from canonical while preserving the local body content.
- **skills/**: Specialized capabilities. Each folder contains a `SKILL.md` (the
  "instruction manual") and a `scripts/` folder (the "limbs"). Skills are
  agent-selected, meaning they only consume tokens when relevant.
- **agents/**: Personas that define how the AI behaves in different modes (e.g.,
  the Architect's reasoning vs. the Executor's speed). They provide the
  "personality" and focus of the AI.

## 12. Glossary of Terms
- **Canonical**: The authoritative, curated state of the knowledge base.
- **Scion**: The canonical knowledge repository. In arboriculture, the scion is the productive cutting — selected for quality, grafted onto rootstock to grow. In this system, the scion repo carries the knowledge (rules, skills, agents) that determines how the AI behaves. It is a separate repo from the rootstock application code.
- **Rootstock**: The platform — the application, the sync engine, the desktop app. Not the knowledge itself.
- **Graft**: The mechanism of distribution from the hub to the spokes. Also the CLI and sync library name.
- **Learning**: The bidirectional first-connect curation cycle where scion and a
  new user's environment exchange knowledge.
- **MasterDetailLayout**: The layout component that owns the horizontal split
  between the list pane and detail panel.
- **Ogham**: The AI persistent memory component embedded in `graft_runtime.db`. Named for the Celtic tree alphabet used by druids to encode knowledge in tree-related marks — here encoding the AI's accumulated experiential knowledge. Distinct from rules and skills (shared canonical knowledge) — the ogham carries personal, dyad-specific memory: session learnings, collaboration calibrations, project-specific context. The `memories` table is the ogham store; the session_briefing hook delivers top-ranked ogham memories into Rule 998 at each session start. Unlike scion knowledge (shared across all projects), ogham is private to this machine and this user-AI relationship.
- **Drift**: The delta between a local environment and the canonical state.
- **Curation Rubric**: The set of quality standards used to evaluate new knowledge.
- **Token Budget**: The limit on context size that dictates how much knowledge can be active at once.
- **Dyad**: The collaborative pair of one human developer and one AI instance.
- **Inbound Drift**: Changes available in canonical (scion `main`) that are not yet local.
- **Outbound Drift**: Local changes that have not yet been pushed to a scion contributor branch.

## 13. AI Memory Layer
Rootstock embeds a persistent AI memory system directly into `graft_runtime.db`.
Unlike rules and skills — which carry *shared* knowledge to all dyads — the
memory layer carries *personal* knowledge specific to this AI instance, this
machine, and this user relationship.

The memory layer is called the **ogham** (after the Celtic tree alphabet used
by druids to encode tree-wisdom). It has three components:

1.  **Storage**: The `memories` table holds claims classified by kind
    (observation, decision, pattern, etc.), tagged for retrieval, and ranked by
    activation score. The `memory_fts` virtual table provides FTS5 full-text
    search. The `memory_links` table records associative relationships between
    memories. Foreign key enforcement and WAL-mode SQLite ensure consistency
    across concurrent writers.

2.  **Capture**: The MCP `write_memory` tool is the primary capture path when
    the MCP server is active. Rule 998 (`temporal-self`) instructs the AI to
    write memories at session end regardless. The `sessionStart` hook serves as
    a supplementary path for structured session-level capture.

3.  **Delivery — a "no wrong door" cascade**:
    - **MCP active**: `serverInstructions` inject a ranked memory summary at
      connection time — always on, no tool call required, available immediately
      in the first message.
    - **MCP absent**: The `sessionStart` hook queries `graft_runtime.db` and
      writes ranked memories into Rule 998's `<!-- ROOTSTOCK:MEMORY:START -->`
      section before the session begins.
    - **Baseline**: Rule 998 always carries the manually authored self-portrait
      as the floor — present even with no hook and no MCP.

The cascade ensures memory is always present at session start. The MCP path is
richer (dynamic, queryable, updatable mid-session); the file path is always
available as a fallback; Rule 998 is the unconditional floor.

The ogham is private to this machine and this user-AI relationship. It never
reaches canonical (scion main). Future phases will enable serialized portability
via user contributor branches.

## 14. Autonomous Operation Model

Rootstock is designed to require minimal user attention for knowledge maintenance. The goal: the AI manages the knowledge environment autonomously within well-defined boundaries, escalating to the user only at permission-required boundaries.

### Auto-Sync Architecture

Sync is event-driven, not time-polled. The Rootstock app (running persistently as the sync daemon) handles all git operations. The AI produces knowledge (writes to `.cursor/`); the app discovers and propagates it.

| Event | Action |
| :--- | :--- |
| Session close (stop hook) | Auto-push local `.cursor/` changes to contributor branch |
| Significant `.cursor/` write | Debounced push (45s) — app file watcher detects and queues |
| App startup | Fetch check — pull if scion has advanced |
| Background (every 20 min) | Pull check — notify if scion has advanced, don't auto-apply |

### Canonical Push-Down Model

After curation, scion **pushes** canonical down to all contributor branches rather than waiting for contributors to pull. The policy layer handles conflicts automatically:
- **0–199 range (overwrite)**: Canonical wins. Local modifications to these files surface as synthesis prompts for resolution.
- **200+ range (protect)**: Never touched by canonical push. No conflict possible.
- **rootstockignore entries**: Excluded entirely.

When a genuine conflict exists (same 0–199 file modified both locally and in canonical), the app surfaces a parameterized synthesis prompt for the user to route to an AI thread for resolution. The resolution updates the contributor branch; the next curation cycle absorbs it into canonical.

### Four-Level Sensitivity Gradient

The pre-push scanner (future) enforces these levels before any git operation:

1. **Accidental personal information** — names, identifiers, personal details in rules or skills. Caught by curation review.
2. **Project-private context** — internal architecture decisions or company-specific terminology in canonical-bound files. Caught by policy classification.
3. **Credentials and API keys** — pre-push scanner with regex patterns and high-entropy string detection. Hard block before any git operation.
4. **Structural leakage** — individually benign content that reveals sensitive information in aggregate. Caught by human curation review.

### Autonomous Operation Boundaries

The AI operates autonomously within the contributor branch and local environment. Permission check-ins are required only for:

- Modifying canonical (`scion main` — requires curation + human review)
- Touching user-protected zones (200+ rules, rootstockignore entries)
- External push when a merge conflict exists on the remote
- Escalating a decision to another user's curator agent

Everything else — sync operations, memory management, health checks, contributor branch updates — runs without interruption.

### 14.1 Telemetry and Runtime Instrumentation
Rootstock instruments both runtime layers by default, then controls export at
runtime through explicit user consent.

- **Rust runtime**: Uses `tracing`. With no active subscriber, call sites are
  effectively near-zero overhead (one atomic load check). Rootstock does not set
  `max_level_release`; desktop debugging benefits from attaching subscribers in
  production when needed.
- **Frontend runtime**: Uses a thin `track(event, data?)` wrapper gated by an
  `enabled` boolean. Disabled mode is one predicted branch and effectively free.
- **Consent model**: Telemetry is opt-in via a Settings toggle, persisted in
  `graft_runtime.db`.

Design principle: instrument freely at build time, attach exporters at runtime
based on user consent. The instrumentation call sites stay stable; only the
runtime attachment changes.
