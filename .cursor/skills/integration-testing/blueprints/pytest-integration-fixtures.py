# BLUEPRINT: Shared Integration Test Fixtures (Python)
# STRUCTURAL: Module layout, fixture dict pattern, pytest fixture registration
# ILLUSTRATIVE: Model names, field names, and domain-specific values are replaceable

"""Shared fixtures valid against both Pydantic (backend) and Zod (frontend).

Keep in sync with ts-integration-fixtures.ts.
"""

from __future__ import annotations

import copy

import pytest

# ILLUSTRATIVE: Replace with your domain's entity shape
VALID_CONFIG: dict = {
    "name": "Test Entity",
    "nodes": [
        {
            "id": "node-1",
            "type": "sourceType",           # ILLUSTRATIVE: node type enum value
            "position": {"x": 100, "y": 100},
            "data": {
                "name": "My Source",
                "url": "https://api.example.com",
                "method": "GET",
                "timeout": 30,
            },
        }
    ],
    "edges": [],
}

# ILLUSTRATIVE: Add invalid variants for every validation rule under test
INVALID_CONFIGS: dict[str, dict] = {
    "empty_name": {**VALID_CONFIG, "name": ""},
    "missing_required": {**VALID_CONFIG, "nodes": []},
    "invalid_field": {
        **VALID_CONFIG,
        "nodes": [
            {
                **VALID_CONFIG["nodes"][0],
                "data": {
                    **VALID_CONFIG["nodes"][0]["data"],
                    "url": "not-a-url",     # ILLUSTRATIVE: field under test
                },
            }
        ],
    },
}


@pytest.fixture
def valid_config() -> dict:
    # STRUCTURAL: deepcopy prevents mutations in one test from leaking into others
    return copy.deepcopy(VALID_CONFIG)


@pytest.fixture
def invalid_configs() -> dict[str, dict]:
    return copy.deepcopy(INVALID_CONFIGS)
