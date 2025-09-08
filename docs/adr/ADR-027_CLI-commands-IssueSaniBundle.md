# ADR-027: CLI UX for IssueSaniBundle Generation

**Status:** Proposed  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  

## Context
UiPath developers need a **low-friction** way to produce sanitized debug packages for bug reports.  
The CLI should expose simple, memorable commands with predictable output, while leaving room for future extensions (pseudonymization, policy overrides).  

## Decision
Introduce a `diag` command group with the following subcommands:  

- `rpax diag package`  
  - Default: generates a redacted `IssueSaniBundle` in ZIP form.  
  - Output filename: `rpax-IssueSaniBundle-<UTC-timestamp>.zip`  
  - Default contents: config snapshot, environment report, parser errors, parser behavior, lake index, manifest.  
  - Redaction policy: drop user data as per ADR-026.  

- Options:  
  - `--out <path>` → write ZIP to custom location.  
  - `--dry-run` → preview redaction (list dropped fields, no files written).  
  - `--allow-host-info` → opt-in to include OS username/hostname in env report.  
  - `--include <section>` (future) → selectively add artifacts.  

## UX Principles
- **Safe by default:** always produce redacted bundles, never raw.  
- **Deterministic filenames:** easy to find and attach.  
- **Transparent:** show which fields were dropped in dry-run.  
- **Extensible:** flags reserved for pseudonymization and selective inclusion.  

## Consequences
- Users can confidently attach `IssueSaniBundle` to GitHub issues.  
- Corporate environments see no telemetry or data exfiltration.  
- Provides a natural upgrade path to pseudonymization and richer diagnostics.  

## Alternatives
- Provide bundle generation only via API (rejected; too high barrier for initial users).  
- Include raw lake data (rejected; unsafe).  
