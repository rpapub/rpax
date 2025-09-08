# ADR-001: Parsing XAML-based Workflow Projects

**Status:** Implemented (Updated 2025-09-08)  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

## Context

Analysis of Windows Workflow Foundation (WF) and UiPath XAML workflows is required. Different approaches exist to extract call graphs, arguments, and activity structure. Each option offers trade-offs in accuracy, complexity, and resilience to vendor changes.

## Options

### Option A — Strict (Schema/Namespace-Aware)

* Use `lxml` + `defusedxml` + `xmlschema` with explicit namespace mappings.

**Pros**

* High precision and strong validation.
* Clear error reporting.
* Future-proof if schemas remain stable.

**Cons**

* Heavy setup and maintenance.
* Fragile under vendor namespace evolution.
* High complexity for small teams or solo work.

---

### Option B — Pattern-Matching (Namespace-Agnostic)

* Parse XML ignoring namespaces; detect activities and arguments via local-name heuristics and structural patterns.

**Pros**

* Simple, fast to implement.
* Resilient to version and namespace churn.
* Independent of vendor schemas or SDKs.

**Cons**

* Semantics only approximate.
* Possibility of false positives and negatives.
* Requires iterative tuning with project samples.

---

### Option C — CLR Bridge (Semantic Loader) \[Low Priority]

* Leverage .NET (`ActivityXamlServices.Load`) via pythonnet or gRPC to load WF activity graphs directly.

**Pros**

* Provides accurate WF semantics.
* Aligns with actual runtime behavior of workflows.

**Cons**

* Requires presence of UiPath/WF assemblies.
* Constrained to Windows/.NET environments.
* Deployment and licensing challenges.
* Fragile when packages are missing.

---

## Amendment Notes (2025-09-08)

**What Changed**: Status updated from Proposed to Implemented, added implementation status section
**Why Amended**: Pattern-matching approach has been successfully implemented and is operational in v0.0.3
**Impact**: Confirms the architectural decision is validated through working implementation

## Decision

* **Go:** Proceed with **Option B (Pattern-Matching)** as baseline for analysis.
* **No-Go:** Do not implement **Option A (Strict)** at this stage due to maintenance burden.
* **No-Go (low priority):** Postpone **Option C (CLR Bridge)** unless access to full UiPath assemblies and a Windows/.NET runtime environment is guaranteed.

## Implementation Status (Updated 2025-09-08)

* **v0.0.1:** ✅ Core implementation with lxml + defusedxml (ADR-015)
* **v0.0.2:** ✅ Enhanced XAML analysis with activity detection and package extraction
* **v0.0.3:** ✅ Production-ready pattern-matching parser with comprehensive test coverage

## Consequences

* Enables resilient parsing across UiPath versions and namespace changes
* Implemented by parser layer (ADR-007) using lenient capture (ADR-008)
* Foundation for all downstream artifact generation (ADR-009)

## Related ADRs

* ADR-007: Parser requirements implementing this approach
* ADR-008: Lenient parsing strategy aligns with pattern-matching tolerance
* ADR-015: lxml chosen as implementation technology for pattern matching
