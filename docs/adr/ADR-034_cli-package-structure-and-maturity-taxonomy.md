# ADR-034: CLI Package Structure and Command Maturity Taxonomy

**Status:** Accepted
**Date:** 2026-03-08
**Consulted:** ADR-003 (CLI Surface), ADR-024 (Blueprint Decorators)

## Context

`src/rpax/cli.py` grew to ~4,500 lines as a single module. Splitting it by moving
it to a differently-named file only relocates the problem. Future work requires:

- Vendor-namespaced sub-apps (UiPath today, AutomationAnywhere/SAP later)
- A public command surface that signals stability to users
- A mechanism to graduate commands from experimental → prod without breaking scripts

A package structure is needed now so future additions are purely additive (new
files, no restructuring). The maturity taxonomy is the mechanism that controls
what the root `rpa-cli --help` surfaces to the user.

## Decision

### 1. `cli` becomes a package

`src/rpax/cli.py` is replaced by `src/rpax/cli/`:

```
src/rpax/cli/
├── __init__.py        # exports app — pyproject.toml entry point unchanged
├── main.py            # root Typer app, version callback, signal handlers, root aliases
├── decorators.py      # api_expose (moved from cli.py) + make_command_factories
└── uipath/
    ├── _app.py        # uipath_app instance + maturity factory tuple
    ├── __init__.py    # imports _app.py, imports commands to register, re-exports
    └── commands.py    # all UiPath commands (~4,300 lines, migrated verbatim)
```

`pyproject.toml` entry point `rpa-cli = "rpax.cli:app"` is unchanged —
`cli/__init__.py` re-exports `app` from `main.py`.

Future vendor namespace: `src/rpax/cli/aa/` — same shape, zero interference.
Future domain split: `uipath/commands.py` → `uipath/parse.py`, `uipath/list.py`, etc.
Both are additive file changes, no structural refactoring.

### 2. Command maturity taxonomy

Four maturity levels, implemented as decorator factories bound to a Typer app:

| Level | Factory | Help panel | Hidden | Meaning |
|-------|---------|------------|--------|---------|
| `prod` | `@command()` | default | no | Stable; breaking changes require a deprecation cycle |
| `experimental` | `@experimental()` | Experimental | no | Preview; interface may change |
| `plumbing` | `@plumbing()` | — | yes | Internal; callable but not advertised |
| `beta` | `@beta()` | — | yes | Feature-flagged; not for general use |

Factories are created by `make_command_factories(app)` in `decorators.py` and
bound to a specific Typer app at module load time. Each factory tags the
decorated function with `func._rpax_maturity = level` for introspection.

### 3. Root help surface = classified commands only

The root `rpa-cli --help` shows **only commands that have been explicitly classified**:

```
╭─ Commands ──────────────────────────╮
│ bump    prod — only classified prod │
│ parse   experimental alias          │
│ explain experimental alias          │
│ uipath  vendor sub-app              │
╰─────────────────────────────────────╯
```

Unclassified commands (all others) are reachable exclusively via the vendor
sub-app: `rpa-cli uipath <command>`. They are not aliased at the root until a
maturity decision is made. This is intentional — no false classification, and
easy to audit what still needs a decision.

`parse` and `explain` are experimental but are aliased at the root to avoid
breaking existing scripts. Their `_rpax_maturity` tag remains `"experimental"`.
Root aliases are removed when they graduate to prod or after a deprecation cycle.

### 4. Circular import avoidance

`uipath/__init__.py` cannot define `uipath_app` and also import `commands.py`
(which needs `uipath_app`) without a circular dependency. Resolution: `_app.py`
is a dedicated module holding only the Typer app instance and the factory tuple.
Both `__init__.py` and `commands.py` import from `_app.py`.

## Rationale

**Why a package now, not when needed?**
Splitting a module later requires updating every import across the codebase.
Making `cli` a package now costs one refactor; every future split is free.

**Why not one flat `cli/commands.py`?**
The vendor sub-app model (`uipath/`, `aa/`) is a first-class concern. Naming the
directory after the vendor makes the architecture self-documenting.

**Why hide unclassified commands instead of removing their root aliases?**
They never had root aliases in the first place in the new design. The
`uipath` sub-app is the home for all UiPath commands; root is the curated surface.

**Why `_rpax_maturity` on the function instead of a registry?**
The tag travels with the function. Introspection tools (`generate_openapi.py`,
future `rpa-cli api-surface`) can inspect any command without a separate lookup.

## Alternatives Considered

1. **Move `cli.py` → `cli_uipath.py`** — Rejected: relocates the monolith,
   adds no structure, breaks all existing imports.

2. **Plugin system with entry points** — Rejected: overengineered for current
   scale; the vendor sub-app model achieves the same isolation without the
   `importlib.metadata` complexity.

3. **Single flat `cli/` with no vendor subdirectory** — Rejected: when a second
   vendor is added the flat layout would require restructuring again.

4. **Rich help panels only, no `_rpax_maturity` tag** — Rejected: tags enable
   programmatic introspection (API surface generation, coverage reports); panels
   alone are display-only.

## Consequences

**Positive:**
- Root `--help` is a curated product surface, not an implementation dump
- Vendor isolation is structural, not just naming convention
- Maturity level is inspectable at runtime (`cmd._rpax_maturity`)
- Future splits (`uipath/parse.py`, `uipath/list.py`) are additive

**Negative:**
- `rpa-cli list`, `rpa-cli validate`, etc. no longer appear in root `--help`;
  users unfamiliar with `rpa-cli uipath` may not find them initially
- The `_app.py` indirection is non-obvious; the circular import rationale must
  be understood before modifying the package structure

**Neutral:**
- `pyproject.toml` and all test imports of `from rpax.cli import app` are
  unchanged — `cli/__init__.py` re-exports `app`
- Mock patch paths that targeted `rpax.cli.<symbol>` must be updated to
  `rpax.cli.uipath.commands.<symbol>` (one test file updated in this change)

## Related ADRs

- **ADR-003**: CLI surface — root surface is now the prod/experimental subset
- **ADR-024**: `@api_expose()` decorator — moved from `cli.py` to `cli/decorators.py`, interface unchanged
- **ADR-021**: CLI parameter conventions — unaffected; all commands migrated verbatim
