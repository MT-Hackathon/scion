// BLUEPRINT: Zod contract schema and form validation handler
// STRUCTURAL: import, schema definition, submitForm, saveConfig — keep all
// ILLUSTRATIVE: EntityConfig name, field names, field types, enum values — replace per contract

import { z } from 'zod';

// STRUCTURAL: schema mirrors the Pydantic model in pydantic-contract.py field-for-field
export const entityConfigSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  url: z.string().url('Must be a valid URL'),
  method: z.enum(['GET', 'POST', 'PUT', 'DELETE']),
  timeout: z.number().int().min(1).max(300),
  auth_type: z.enum(['none', 'api_key', 'oauth2']).default('none'),
  api_key_ref: z.string().optional()
});

// STRUCTURAL: TypeScript type inferred from schema — never hand-author this type
export type EntityConfig = z.infer<typeof entityConfigSchema>;

// STRUCTURAL: validate at form submit; show inline errors; do not proceed on failure
export function submitForm(
  data: unknown,
  setErrors: (errors: Record<string, string[]>) => void,
  onValid: (config: EntityConfig) => Promise<void>
): void {
  const result = entityConfigSchema.safeParse(data);
  if (!result.success) {
    setErrors(result.error.flatten().fieldErrors);
    return;
  }
  void onValid(result.data);
}

// STRUCTURAL: re-validate immediately before sending; never send unvalidated data
export async function saveConfig(config: EntityConfig): Promise<void> {
  const result = entityConfigSchema.safeParse(config);
  if (!result.success) {
    throw new Error('Invalid config — re-validation failed before API call');
  }
  const response = await fetch('/api/entities', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(result.data)
  });
  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }
}
