# ADR-020: Automatic Inclusion of Known Dependencies in Project Resolution

**Status:** Accepted  
**Date:** 2025-09-05  

## Context

UiPath **Process** projects can declare dependencies (e.g. Libraries, Object Repository packages) in `project.json`.  
When a Process is resolved in the lake, the MCP client often needs to know if the corresponding **Library code** is also available locally.  
Two options:  
- Return only the Process project matched by the query  
- Also return Library dependencies if their source exists in the lake  

## Decision

- **Include dependencies automatically.**  
- If a Process project references a Library dependency and the lake contains a project matching `(name, version)`, then that Library project is **added to the resolution result**.  
- Each dependency is returned as a **separate project block**, with its own resources and metadata.  

## Consequences

- Clients get a complete picture of the Process and any local Libraries it uses.  
- Dependencies are surfaced uniformly with Processes, so resource access is the same.  
- Ambiguity is reduced: clients don’t need to run a second query for dependencies.  
- Cross-version mismatches may exist; these must be explicitly marked in the future.  

## Example

Query:  
```json
{ "query": "prometh" }
````

Result:

```json
{
  "matches": [
    {
      "slug": "purposefulpromethium",
      "name": "PurposefulPromethium",
      "type": "process",
      "version": "5.0.0-alpha"
    },
    {
      "slug": "acme.util.library",
      "name": "Acme.Util.Library",
      "type": "library",
      "version": "1.2.3"
    }
  ]
}
```

Here the Process `PurposefulPromethium` was matched directly, and its Library dependency `Acme.Util.Library` was included because its code also exists in the lake.
