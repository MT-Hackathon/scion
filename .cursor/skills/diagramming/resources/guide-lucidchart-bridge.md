# Lucidchart Bridge Guide

How to move diagrams between Mermaid source (repo) and Lucidchart/Lucidspark (stakeholder presentations).

## Principle

The `.mmd` source file in the repository is the **system of record**. Lucidchart versions are "presentation copies" -- they may have adjusted layout, branding, or annotations added by stakeholders, but the logical structure lives in version control.

## Into Lucidchart (Mermaid to Lucid)

Lucidchart has a native "Diagram as Code" panel that accepts Mermaid syntax directly.

### Steps

1. Open the `.mmd` source file in your editor or on GitLab
2. Copy the entire Mermaid text (everything in the file, including the diagram type declaration like `flowchart TD`)
3. In Lucidchart:
   - Open Insert menu (or press `+`)
   - Select "Diagram as Code"
   - Paste the Mermaid source
   - Click "Generate"
4. Lucidchart creates editable shapes with connections
5. Adjust layout, add branding, annotations as needed for the audience

### Tips

- Simple flowcharts and sequence diagrams import cleanly
- Complex diagrams with many subgraphs may need manual layout adjustment after import
- ER diagrams import but may look different than the Mermaid rendering
- Lucidchart may not support the newest Mermaid syntax features; keep to well-established patterns

## Out of Lucidchart (Lucid to Repo)

There is no automated text export from Lucidchart to Mermaid. When a diagram originates in Lucid and needs to be versioned:

### Steps

1. Export from Lucidchart as **PNG** or **SVG** (File > Export)
2. Place the image in `docs/diagrams/` (shareable profile)
3. Write a corresponding `.mmd` source file that captures the logical structure
4. The `.mmd` becomes the versioned truth going forward
5. Commit both the image (for immediate visibility) and the source (for maintainability)

### Why Manual?

Lucidchart stores diagrams in a proprietary format. Their API exports JSON with shape IDs and coordinates, not logical graph structure. Building an automated converter would be fragile and high-maintenance for low frequency use.

## Lucidspark

Lucidspark does not have the "Diagram as Code" panel. To get Mermaid into Lucidspark:

1. Import into **Lucidchart** first (using steps above)
2. Use Lucid's built-in integration to move/copy the diagram to a Lucidspark board
3. Or: render the Mermaid to SVG locally, import the SVG image into Lucidspark

## When to Use Which

| Audience | Format | How |
|----------|--------|-----|
| Developers (code review, MR) | `.md` with mermaid block | Commit to repo, GitLab renders |
| Developers (local) | `.mmd` file | VS Code/Cursor preview |
| Business stakeholders | Lucidchart | Paste Mermaid into Diagram as Code |
| Email / Jira / Slack | SVG or PNG | Render locally, attach |
| Architecture decision record | `.md` bundle | Commit with `--profile shareable` |
