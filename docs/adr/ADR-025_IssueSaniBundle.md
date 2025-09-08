# ADR-025: Canonical Name “IssueSaniBundle” for Redacted Debug Package

**Status:** Accepted  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

## Decision
Use **IssueSaniBundle** as the canonical, user-facing name for the redacted diagnostic bundle.

## Rationale
- Short, neutral, “hygienic” connotation.
- Clear to non-native speakers and UiPath devs (PascalCase).
- Avoids edgy/jargon terms.

## Scope
- **Docs wording:** `Please attach the rpax IssueSaniBundle generated with rpax diag package.`
- **CLI:** `rpax diag package` (produces redacted bundle by default).
- **Filename:** `rpax-IssueSaniBundle-<UTC-timestamp>.zip`
- **Manifest inside ZIP:** `IssueSaniBundle.manifest.json` (list files + hashes).

## Contents (phase 1)
- `diag/config.snapshot.json` (no secrets).
- `diag/env.report.json` (no user/host by default).
- `diag/parser.errors.jsonl`
- `diag/parser.behavior.json`
- `diag/lake.index.json`
- `README.txt` (what’s included, redaction notes).

## Redaction Policy (defaults)
- Mask selectors, asset names, URLs, file paths.
- Drop usernames/hostnames unless explicitly allowed.
- Policy file: `.rpax-redact.json` (overrides).

## Non-Goals
- No telemetry, no auto-upload, no background network.

## Backwards Compatibility
- Older terms (“bundle”, “flightrecord”) deprecated in docs; keep CLI command stable.
