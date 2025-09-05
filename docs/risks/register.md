# Edge Cases & Foreseen Challenges — TODO (Risk Taxonomy)

- [ ] **RISK-001 — Multiple entry points with same file name (different folders)**
  - [ ] Implement canonical, repo-relative path IDs.

- [ ] **RISK-002 — Dynamic invocations (`Path.Combine`, variables)**
  - [ ] Flag as `invoke-dynamic`.
  - [ ] Optional: heuristics via known roots/dirs.

- [ ] **RISK-003 — Cross-project invokes (paths escaping project root)**
  - [ ] Mark explicitly.
  - [ ] Optional: include with provenance.

- [ ] **RISK-004 — Library projects (public XAML under `Activities/`)**
  - [ ] Treat as exports.
  - [ ] Parse invokes as usual.

- [ ] **RISK-005 — Coded workflows (C#)**
  - [ ] Record presence as `external/coded`.
  - [ ] Skip deep parse in v1.

- [ ] **RISK-006 — Object Repository invokes (helper XAML wrappers)**
  - [ ] Parse as normal XAML workflows.

- [ ] **RISK-007 — Windows-Legacy vs Windows; VB vs C# expressions**
  - [ ] Apply same path rules.
  - [ ] Treat expression differences uniformly (literal recovery only).
- [ ] **RISK-008 — Large projects (1k+ workflows)**
  - [ ] Potential memory/performance issues when parsing or building graphs.
  - [ ] Mitigate with streaming parsers, parallelism, and incremental hashing.

- [ ] **RISK-009 — Inconsistent or corrupted `project.json`**
  - [ ] Missing or malformed fields despite Studio enforcement.
  - [ ] Parser must record `parse_error` events instead of crashing.

- [ ] **RISK-010 — Deprecated schema versions**
  - [ ] Older `schemaVersion` values (e.g., <4.0) may lack fields like `entryPoints`.
  - [ ] Need backward-compatible parsing logic.

- [ ] **RISK-011 — External resource references**
  - [ ] Selectors, Assets, Queues, Config paths may be incomplete or environment-specific.
  - [ ] Store them leniently without assuming resolvability.

- [ ] **RISK-012 — ViewState vs activity tree mismatch**
  - [ ] XAML may contain design-time view state elements with stale IDs.
  - [ ] Parser must tolerate and not depend on them for identity.

- [ ] **RISK-013 — Hidden dependencies**
  - [ ] Activities calling code (InvokeMethod, InvokeCode) introduce non-XAML dependencies.
  - [ ] Represent minimally (`external/invoke`).

- [ ] **RISK-014 — Case sensitivity & path normalization**
  - [ ] Filesystem case-insensitive vs repo case-sensitive mismatch.
  - [ ] Normalize to POSIX-style paths consistently.

- [ ] **RISK-015 — Test cases as roots**
  - [ ] `fileInfoCollection` defines test workflows that behave differently from main entry points.
  - [ ] Must annotate clearly to avoid mixing process vs test graphs.

- [ ] **RISK-016 — Incremental runs / cache drift**
  - [ ] Artifacts may be out of sync with source files if not regenerated.
  - [ ] Consumers must check hash/ETag consistency.
