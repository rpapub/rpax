# ADR-019: Arrays as Canonical Return Shape for MCP Tools

**Status:** Accepted  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  

## Context

MCP tools in the `rpax` ecosystem return structured data derived from the lake.  
Examples: `project.resolve`, `project.resources`, `workflow.activities`, `workflow.metrics`.  

There is a choice of response shapes:  
- Return a single object when only one item matches  
- Return either a single object or an array depending on cardinality  
- Always return arrays, even if length 0 or 1  

Consistency is critical for client simplicity.  

## Decision

- **Always return arrays.**  
- Every MCP tool response will use arrays as the outer structure, even if the result contains a single item.  
- Special cases are not allowed:  
  - 0 results → `[]`  
  - 1 result → `[ { … } ]`  
  - N results → `[ { … }, … ]`  

## Consequences

- **Clients**: never need to branch on type; can always iterate.  
- **Consistency**: identical contract across tools (project-level, workflow-level, activity-level).  
- **Predictability**: API and MCP tools behave the same; arrays are canonical.  
- **Verbosity**: responses may look slightly heavier for single-item cases, but this is outweighed by clarity.  

## Example

Query:  
```json
{ "query": "prometh" }
````

Response (one project match):

```json
{
  "matches": [
    {
      "slug": "purposefulpromethium",
      "name": "PurposefulPromethium",
      "type": "process",
      "version": "5.0.0-alpha"
    }
  ]
}
```

Response (no matches):

```json
{ "matches": [] }
```

Response (multiple matches):

```json
{
  "matches": [
    { "slug": "purposefulpromethium", "name": "PurposefulPromethium", "type": "process" },
    { "slug": "prometheus-tests", "name": "Prometheus Tests", "type": "process" }
  ]
}
```

## Status

This ADR establishes arrays as the canonical response shape for all MCP tool responses in `rpax`.
