# Reference: Canvas Node Types

Node type definitions and styling requirements.

---

## Pattern

### Node Type Categories

| Type | Color | Handles | Purpose |
|------|-------|---------|---------|
| Source | Green | Out-only | Data ingestion |
| Target/Destination | Blue | In-only | Data storage |
| Transform | Purple/Amber | Bidirectional | Data transformation |

### Token-Based Styling

All node visuals must use design tokens, never hardcoded values:

**Color tokens:**
- `--node-color-source` - Source node accent
- `--node-color-transformation` - Transform node accent
- `--node-color-destination` - Destination node accent

**Gradient tokens:**
- `--node-gradient-source` - Source node background
- `--node-gradient-transformation` - Transform node background
- `--node-gradient-destination` - Destination node background

**Border tokens:**
- `--node-border-*` - Idle state borders
- `--node-border-*-active` - Selected state borders

**Shadow tokens:**
- `--node-shadow-*` - Base shadows
- `--node-shadow-*-strong` - Hover/selected shadows

**Handle tokens:**
- `--node-handle-size` - Handle diameter
- `--node-handle-border-width` - Handle border
- `--node-handle-shadow-width` - Handle glow

### Visual Hierarchy Sequence

Copy this sequence from reference implementation:

1. **Gradient background** - Sets base visual
2. **Border** - Defines node boundary
3. **Shadow** - Adds elevation
4. **Overlay** (on hover/selected) - Adds interaction feedback
5. **Outline** (on focus) - Adds keyboard focus indicator

### Theme Considerations

All node tokens automatically adjust for light/dark theme via CSS variable sync. No manual theme checks needed in node components.

---

## Project Implementation

### Universal-API Node Types

| Type | Value | Color Token | Purpose |
|------|-------|-------------|---------|
| API Source | `apiSource` | `--node-color-source` | API data ingestion |
| Database Target | `databaseTarget` | `--node-color-destination` | Database storage |
| Transform | `transform` | `--node-color-transformation` | Data transformation |

### Reference Implementation

Canonical node implementation (planned): `app/frontend/src/lib/components/nodes/SourceNode.svelte`

For the structural scaffold to adapt from, see `blueprints/canvas-node.svelte` in this skill.

```svelte
<div 
  class="node"
  class:selected
  style="
    background: var(--node-gradient-source);
    border: 2px solid var(--node-border-source);
    box-shadow: var(--node-shadow-source);
  "
>
  <div class="node-header" style="border-left: 4px solid var(--node-color-source)">
    <h3>{data.label}</h3>
  </div>
  <div class="node-content">
    <!-- Node content -->
  </div>
</div>
```

### Token File Locations

| Purpose | Path |
|---------|------|
| Node tokens | `app/frontend/src/app.css` |
| Config node tokens | `--config-node-*` in `app.css` |
| Token values | `app/frontend/src/lib/config/default_app_settings.json` (planned) |
