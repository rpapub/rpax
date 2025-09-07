# ADR-018: Project Identity and UUID Trust Policy

**Status:** Accepted  
**Date:** 2025-09-05

## Context

When generating project slugs for multi-project lake storage, rpax must decide how to handle UiPath project.json files that contain `projectId` fields. Some projects have unique UUIDs while others lack this field entirely.

A key concern is template projects: users might clone a template repository without changing the `projectId` UUID, leading to potential collisions. This creates a question of whether rpax should validate UUID uniqueness or trust user-provided values.

## Decision

**Trust the `projectId` UUID as provided by the user.** Do not validate uniqueness or attempt to detect template cloning scenarios.

## Rationale

1. **User Responsibility**: Project identity management is fundamentally a user concern. If users clone templates without updating project metadata, that is a development workflow issue, not a parser tool issue.

2. **Simplicity**: UUID validation would require complex collision detection across all known projects, adding significant implementation complexity.

3. **Performance**: Avoiding UUID validation keeps parsing fast and stateless.

4. **UiPath Studio Behavior**: UiPath Studio itself trusts projectId values and generates unique UUIDs when creating new projects. We should follow this precedent.

5. **Fallback Strategy**: For projects without projectId, we fall back to content hashing, which naturally handles the uniqueness concern.

## Implementation

```python
def generate_project_slug(self, project_json_path: Optional[Path] = None) -> str:
    if self.project_id:
        # Trust user-provided UUID, use first 8 characters
        return self.project_id[:8]
    
    # Fallback for projects without projectId
    name_part = normalize_name(self.name)
    if project_json_path:
        hash_val = hash_content(project_json_path)[:8]
        return f"{name_part}-{hash_val}"
    
    return name_part or "unknown"
```

## User Guidance

Users should ensure:
- New projects have unique `projectId` values (UiPath Studio handles this automatically)
- When cloning template projects, update the `projectId` field
- Project names are descriptive for projects lacking `projectId`

## Consequences

### Benefits
- Simple, fast implementation
- Consistent with UiPath Studio behavior
- Clear separation of concerns (rpax = parsing, user = project management)
- Graceful handling of both modern and legacy project formats

### Risks
- Potential slug collisions if users clone templates carelessly
- No built-in protection against accidental project identity conflicts

### Mitigation
- Clear documentation about project identity best practices
- Warning messages when parsing projects without `projectId`
- Lake structure naturally isolates projects by slug, limiting collision impact

## Related ADRs

- ADR-014: Identity & Disambiguation (Multi-Project Lake) - defines composite identity model
- ADR-017: Data Lake Nomenclature and Design Influence - specifies project slug usage

## Alternatives Considered

**A. UUID Validation**: Check for uniqueness across all known projects
- Rejected: Adds complexity, requires global state, performance overhead

**B. UUID Generation**: Replace user UUIDs with rpax-generated ones  
- Rejected: Breaks user expectations, loses integration with UiPath tooling

**C. Hybrid Approach**: Trust UUIDs but warn on duplicates
- Rejected: Still requires collision detection complexity