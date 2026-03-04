# Examples: Configuration Persistence

Pipeline configuration save/load patterns.

---

## Pattern

### Pipeline Config Structure

All pipeline configurations must contain:

```typescript
interface PipelineConfig {
  version: string;        // Semver format
  nodes: NodeConfig[];    // Node definitions
  edges: EdgeConfig[];    // Edge connections
  metadata: {
    name: string;
    description?: string;
    created: string;      // ISO8601 datetime
    modified: string;     // ISO8601 datetime
  };
}
```

### Schema Validation with Zod

```typescript
import { z } from 'zod';

const nodeSchema = z.object({
  id: z.string(),
  // NOTE: Replace with project-specific types (see Project Implementation below)
  type: z.enum(['apiSource', 'transform', 'databaseTarget']),
  position: z.object({ x: z.number(), y: z.number() }),
  data: z.record(z.unknown())
});

const edgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  sourceHandle: z.string().optional(),
  targetHandle: z.string().optional()
});

const pipelineConfigSchema = z.object({
  version: z.string().regex(/^\d+\.\d+\.\d+$/),
  nodes: z.array(nodeSchema),
  edges: z.array(edgeSchema),
  metadata: z.object({
    name: z.string(),
    description: z.string().optional(),
    created: z.string().datetime(),
    modified: z.string().datetime()
  })
}).refine(
  (config) => {
    const ids = new Set(config.nodes.map(n => n.id));
    return ids.size === config.nodes.length;
  },
  { message: 'Duplicate node IDs found' }
);
```

### Save Flow

```typescript
async function savePipeline(nodes: Node[], edges: Edge[]): Promise<void> {
  const config = buildConfig(nodes, edges);
  
  // Validate before saving
  const result = pipelineConfigSchema.safeParse(config);
  if (!result.success) {
    throw new Error(`Invalid config: ${result.error.message}`);
  }
  
  // Save to backend or download
  await saveToBackend(result.data);
  // OR
  downloadAsFile(result.data);
}
```

### Load Flow

```typescript
async function loadPipeline(source: 'file' | 'backend'): Promise<PipelineConfig> {
  const json = await fetchConfig(source);
  
  // Validate schema
  const result = pipelineConfigSchema.safeParse(json);
  if (!result.success) {
    throw new Error(`Invalid config: ${result.error.message}`);
  }
  
  // Auto-migrate if old version
  return migrateVersion(result.data);
}
```

### Version Migration

```typescript
function migrateVersion(config: PipelineConfig): PipelineConfig {
  if (config.version === CURRENT_VERSION) return config;
  
  // Migration logic for each supported old version
  if (config.version === '0.9.0') {
    return { ...config, version: '1.0.0', /* transform fields */ };
  }
  
  throw new Error(`Unsupported version: ${config.version}`);
}
```

### Auto-Save Pattern

```typescript
// Auto-save every 30 seconds
const AUTOSAVE_INTERVAL = 30000;
const MAX_AUTOSAVE_SIZE = 5 * 1024 * 1024; // 5MB

function startAutoSave(getState: () => PipelineConfig): void {
  setInterval(() => {
    const config = getState();
    const json = JSON.stringify(config);
    
    if (json.length > MAX_AUTOSAVE_SIZE) {
      console.warn('Auto-save skipped: exceeds size limit');
      return;
    }
    
    localStorage.setItem('pipeline_autosave', json);
  }, AUTOSAVE_INTERVAL);
}

// Prompt before loading auto-saved data
function loadAutoSave(): PipelineConfig | null {
  const saved = localStorage.getItem('pipeline_autosave');
  if (!saved) return null;
  
  const confirmed = confirm('Load auto-saved pipeline?');
  return confirmed ? JSON.parse(saved) : null;
}
```

---

## Project Implementation

### Universal-API Node Types

```typescript
type: z.enum(['apiSource', 'transform', 'databaseTarget'])
```

### File Extension

Use `.pipeline.json` for all pipeline configuration files.

### File Locations

| Purpose | Path |
|---------|------|
| Pipeline Store | `app/frontend/src/lib/stores/pipelineStore.ts` (planned) |
| Config Schema | `app/frontend/src/lib/types/pipeline.ts` (planned) |
| Save/Load Utils | `app/frontend/src/lib/utils/pipelineConfig.ts` (planned) |

### Backend Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Save | POST | `/api/pipelines` |
| Load | GET | `/api/pipelines/{id}` |
| List | GET | `/api/pipelines` |
| Draft | POST | `/api/pipelines/drafts` |

### Settings vs Pipeline Configs

```typescript
// ❌ BAD: Mixing concerns
const config = {
  nodes: [...],
  theme: 'dark', // Belongs in settingsStore
};

// ✅ GOOD: Separate concerns
const pipelineConfig = { version, nodes, edges, metadata };
import { settingsStore } from '$lib/stores/settingsStore';
```
