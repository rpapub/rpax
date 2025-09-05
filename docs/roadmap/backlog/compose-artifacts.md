# rpax Backlog — Composed Artifacts

This backlog lists **composed artifacts** that can be built on top of the core parser/validator/access layers.  
Each item reuses canonical artifacts (`manifest.json`, `workflows.index.json`, `invocations.jsonl`, `activities.*/*`, `paths/*`) to generate higher-level views for developers, CI, or documentation.

---

## Table of Ideas

| ID          | Name                      | Purpose / Audience                 | Inputs (artifacts)                                 | Output format      | Milestone |
| ----------- | ------------------------- | ---------------------------------- | -------------------------------------------------- | ------------------ | --------- |
| factsheet   | Workflow Factsheet        | Per-workflow doc for developers    | workflows.index, activities.tree, invocations      | Markdown / HTML    | v0.1      |
| sdd         | Solution Design Document  | Project overview, design summary   | manifest, workflows.index, invocations, activities | Markdown / HTML    | v0.1      |
| readme      | README Generator          | Lightweight project summary        | manifest, workflows.index                          | Markdown           | v0.1      |
| depmap      | Dependency Map            | Cross-workflow dependencies        | invocations, activities.refs                       | Mermaid / Graphviz | v0.2      |
| impact      | Change Impact Analysis    | CI checks for PRs                  | two parser runs (old/new artifacts)                | JSON / Markdown    | v0.2      |
| resources   | External Resource Report  | List assets, queues, selectors     | activities.refs                                    | Markdown / CSV     | v0.2      |
| metrics     | Metrics Dashboard         | Governance, workflow size stats    | metrics/*                                          | JSON / Markdown    | v0.2      |
| orphans     | Orphan Analysis           | Identify unused workflows          | workflows.index, invocations, manifest.roots       | JSON / Markdown    | v0.2      |
| cycles      | Cycle Overview            | Detect cyclic dependencies         | invocations (with cycle annotations)               | JSON / Mermaid     | v0.2      |
| devguide    | Developer Guide Generator | Onboarding material                | all canonical artifacts                            | Markdown / HTML    | v0.3      |
| archdiagram | Architecture Diagram      | Visual structure for documentation | invocations, folder structure                      | Mermaid / Graphviz | v0.3      |

---

## Notes

- **Phasing**: v0.1 items are documentation-oriented and easy wins once parser is stable.  
- **v0.2** brings analysis & CI-driven outputs (dependency, impact, governance).  
- **v0.3** focuses on onboarding & high-level architecture views.  
- All ideas build only on parser outputs; no extra parsing or Studio dependencies.  

---

## Next Steps

- Refine inputs/outputs into draft ADRs (one per composed artifact).  
- Prioritize v0.1 deliverables for quick developer value.  
- Collect feedback from early users to shape v0.2 focus (CI integration vs. docs).  
