# build

Start by locating the plan artifact in `.cursor/plans/` — or the user will point you to one. Read it before doing anything else.

If no plan exists: say so, suggest `/design` first, and ask whether to proceed anyway. Some tasks don't need a full design phase — use judgment. But if a plan exists, the design decisions are settled. Don't re-derive them.

You have agency here and are the orchestrator. Lead your team.

## Executing the Plan

Read the delegation structure from the plan and execute phases in order. The cascade analysis and risk inventory are already done — trust them. Brief each specialist with the plan's phase detail; they should be able to execute without making architectural decisions mid-flight.

Agent autonomy stays high: use researchers and explorers when unknowns surface mid-execution (not mid-design), and consult the Architect when execution reveals something the plan didn't anticipate. These are execution surprises — not invitations to re-open design questions.

## Quality Standard

There's no review gate. The quality standard lives in the pipeline: agents self-verify, QA has fix authority, the subagentStop hook runs automated checks, and your own critical eye is always-on.

What you produce should be something you'd stand behind. Would you get on a space shuttle running this code?

I'm here if you need me. If the work surfaces something worth collaborating on before proceeding, come find me — but you're also empowered to use your judgment.
