# ADR-026: Vendor vs User Data Delineation in IssueSaniBundle

**Status:** Proposed  
**Date:** 2025-09-06  

## Context
The `IssueSaniBundle` is designed as a redacted debug package suitable for sharing in public issue trackers.  
To prevent leakage of sensitive corporate/user information, we must define which data is **vendor-safe** and which is **user-originated**.  
Vendor data may be retained; user data must be dropped or pseudonymized.  

## Decision
Adopt a **policy-driven delineation** of fields:

- **Keep (vendor-safe):**  
  - Activity types (`UiPath.Core.Activities.*`)  
  - Package names and versions  
  - UiPath schema/studio versions  
  - rpax schema/tool versions  
  - Error kinds/codes (without raw text)  
  - Metrics and counts  

- **Drop (user-originated, first iteration):**  
  - Workflow/file paths  
  - Workflow names (unless recognized as vendor-internal, e.g. ending with `_`)  
  - DisplayNames (same rule as above)  
  - Arguments and variable names  
  - Selectors, assets, queues, file paths, URLs  
  - Host/user information  
  - Comments/annotations  

- **Future (stubbed as not implemented yet):**  
  - Pseudonymization of identifiers (workflow IDs, variables, references) using deterministic tokens.  

## Implementation

### Redaction Policy Structure
The redaction policy is defined as JSON with explicit field classification:

```json
{
  "policyVersion": "0.1",
  "keep": [
    "activityTypes",
    "packages",
    "uipathVersions",
    "rpaxVersions",
    "metrics",
    "errorKinds"
  ],
  "drop": [
    "workflowPaths",
    "workflowNames",
    "displayNames",
    "argNames",
    "varNames",
    "selectors",
    "assets",
    "queues",
    "filePaths",
    "urls",
    "hostInfo",
    "usernames",
    "comments",
    "annotations"
  ],
  "pseudonymize": [
    "wfId",
    "nodeId",
    "refs"
  ],
  "notes": "In v0.0.1–v0.1 pseudonymize is not implemented; these fields are dropped with a warning."
}
```

### Implementation Notes
- Introduce a `redaction.policy.json` or `.rpax-redact.json` file defining keep/drop/pseudonymize for each field.  
- In v0.0.1–v0.1, only **drop** is supported.  
- Pseudonymization (`pseudonymize: true`) is parsed but results in a warning: `"not implemented, falling back to drop"`.  

## Consequences
- Ensures no user data leaks in first iteration bundles.  
- Provides forward-compatible structure for pseudonymization.  
- Slightly reduced debugging fidelity until pseudonymization is implemented.  

## Alternatives
- Hardcode redaction rules (rejected, no flexibility).  
- Implement pseudonymization immediately (rejected, too complex for v0.0.1).  
