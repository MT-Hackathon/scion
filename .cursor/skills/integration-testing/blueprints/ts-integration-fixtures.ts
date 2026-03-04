// BLUEPRINT: Shared Integration Test Fixtures (TypeScript)
// STRUCTURAL: Export pattern, const objects, invalid variant mapping
// ILLUSTRATIVE: Type names, field names, and domain values are replaceable

// ILLUSTRATIVE: Replace with your domain's Zod-validated type
export const validConfig = {
  name: 'Test Entity',
  nodes: [
    {
      id: 'node-1',
      type: 'sourceType' as const,        // ILLUSTRATIVE: node type enum value
      position: { x: 100, y: 100 },
      data: {
        name: 'My Source',
        url: 'https://api.example.com',
        method: 'GET' as const,
        timeout: 30,
      },
    },
  ],
  edges: [] as unknown[],
};

// ILLUSTRATIVE: Add invalid variants for every validation rule under test
export const invalidConfigs = {
  emptyName: { ...validConfig, name: '' },
  missingRequired: { ...validConfig, nodes: [] },
  invalidField: {
    ...validConfig,
    nodes: [
      {
        ...validConfig.nodes[0],
        data: {
          ...validConfig.nodes[0].data,
          url: 'not-a-url',               // ILLUSTRATIVE: field under test
        },
      },
    ],
  },
};
