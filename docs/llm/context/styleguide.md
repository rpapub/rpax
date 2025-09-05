```markdown
# Python Minimal Style Guide

## 1. Formatting
- Follow **PEP 8** (https://peps.python.org/pep-0008/).
- Use **Black** (line length 88) and **isort** (profile=black).
- Use **Ruff** for linting; keep zero warnings in CI.

## 2. Naming
- Modules/packages: `snake_case`.
- Variables/functions/methods: `snake_case`.
- Classes/Exceptions: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.

## 3. Imports
- Absolute imports preferred; standard lib → third-party → local.
- No wildcard imports.
- Defer heavy/optional imports inside functions when necessary.

## 4. Types
- Use **PEP 484** type hints everywhere public.
- Enable **PEP 563/649** behavior via `from __future__ import annotations` (Python ≥3.11 not needed).
- Validate with **mypy** (strict where feasible).
- Distribute typing with **PEP 561** (include `py.typed`).

## 5. Docstrings
- Follow **PEP 257**.
- Public modules, classes, functions: docstring required.
- One-line summary first; include Args/Returns/Raises sections.
- Keep README high level; API details in docs.

## 6. Exceptions & Logging
- Raise specific exceptions; avoid bare `except`.
- No control flow via exceptions.
- Use `logging` (module-level logger); no print in libraries.
- Include context, avoid sensitive data.

## 7. Functions & Classes
- Prefer small, pure functions.
- Limit function args; group with dataclasses or typed dicts if needed.
- Avoid mutable default args.
- Use `@dataclass(frozen=True)` for value objects.

## 8. Collections & Iteration
- Prefer comprehensions and generators.
- Use `pathlib.Path` over `os.path`.
- Use `Enum` for closed sets.

## 9. Concurrency
- Choose `asyncio` for I/O; `concurrent.futures` for CPU-bound via processes.
- Keep boundaries explicit; avoid mixing sync/async without adapters.

## 10. Configuration
- Read config from env/files; parse with `pydantic` or `dataclasses`.
- No global mutable state.

## 11. Testing
- Use **pytest**.
- Structure: `tests/` mirrors package layout.
- Aim for fast, isolated tests; use fixtures and tmp paths.
- Measure coverage; enforce threshold in CI.

## 12. Packaging
- Use **PEP 621** metadata in `pyproject.toml`.
- Versioning per **PEP 440**.
- Include `LICENSE`, `AUTHORS.md`, `README.md`, `py.typed` (if typed).

## 13. CLI
- Use `argparse` or `typer/click`.
- Provide `--version`, `--help`; non-zero exit codes on failure.

## 14. Security
- Parse XML with `defusedxml` when applicable.
- Avoid `eval/exec`; validate external inputs.
- Pin dependencies; use `pip-tools` or `uv` lockfiles.

## 15. Git & CI
- Enforce formatting/lint/type/tests in CI.
- Pre-commit hooks: black, isort, ruff, mypy, pytest (quick subset).

## 16. File Layout (library)

```bash
project/
docs/...
src/rpax/...
tests/
pyproject.toml
README.md
LICENSE
AUTHORS.md
```

## 17. Comments
- Explain *why*, not *what*.
- Use TODO/FIXME with issue links.

---
References: PEP 8, 257, 484, 561, 621, 440.
