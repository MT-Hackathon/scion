# New Tool Checklist

- Description follows the `when -> outcome -> boundary` pattern
- Category assignment reflects user intent and privilege level, not just code adjacency
- If always-on, token cost is justified by daily-driver or lifecycle-primitive status
- Schema property descriptions exist for every parameter
- Examples are present only on high-ambiguity parameters
- Batch-capable inputs accept `string | string[]` where cross-item use is plausible
- `CATEGORY_MAP` and any server instructions are updated from the same registry source
- Annotations are set correctly, including `read_only_hint` and `destructive_hint`
- Destructive operations are isolated in a gated category separate from read operations
- Sampling-capable tools expose an explicit `mode` parameter with `heuristic` as the default
