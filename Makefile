# Makefile for rpax development tasks
# Uses PowerShell Core (pwsh) for cross-platform compatibility
# Run with: make parse-all-corpuses

# Configuration
PYTHON := uv run
RPAX := $(PYTHON) -m rpax.cli
SHELL := pwsh

# Test corpus paths (Windows-specific - these targets won't run on Ubuntu)
CORPUS_CORE1 := D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001/project.json
CORPUS_CORE10 := D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000010/project.json
CORPUS_FROZENCHLORINE := D:/github.com/rpapub/FrozenChlorine/project.json
CORPUS_CPRIMA_VIOLATION := D:/github.com/rpapub/PropulsiveForce/CPRIMA-USG-001_ShouldStopPresence/Violation/project.json
CORPUS_CPRIMA_NOVIOLATION := D:/github.com/rpapub/PropulsiveForce/CPRIMA-USG-001_ShouldStopPresence/NoViolation/project.json

# Lake directory for cross-project testing
RPAX_LAKE := .rpax-test-lake

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  parse-all              Parse all test corpus projects (both legacy and v0 schemas)"
	@echo "  parse-all-corpuses     Parse all test corpus projects (alias)"
	@echo "  parse-all-legacy       Parse all test corpus projects (legacy schema only)"
	@echo "  parse-all-v0           Parse all test corpus projects (v0 schema only)"
	@echo "  parse-corpus-core1     Parse c25v001_CORE_00000001 corpus (legacy)"
	@echo "  parse-corpus-core10    Parse c25v001_CORE_00000010 corpus (legacy)"
	@echo "  parse-frozenchlorine   Parse FrozenChlorine corpus (legacy)"
	@echo "  parse-cprima-violation Parse CPRIMA violation corpus (legacy)"
	@echo "  parse-cprima-noviolation Parse CPRIMA no-violation corpus (legacy)"
	@echo "  parse-v0-corpus-core1  Parse c25v001_CORE_00000001 corpus (v0 schema)"
	@echo "  parse-v0-corpus-core10 Parse c25v001_CORE_00000010 corpus (v0 schema)"
	@echo "  parse-v0-frozenchlorine Parse FrozenChlorine corpus (v0 schema)"
	@echo "  parse-v0-cprima-violation Parse CPRIMA violation corpus (v0 schema)"
	@echo "  parse-v0-cprima-noviolation Parse CPRIMA no-violation corpus (v0 schema)"
	@echo "  test-projects          Test cross-project access commands"
	@echo "  test                   Run test suite"
	@echo "  lint                   Run linting (ruff + mypy)"
	@echo "  format                 Auto-format code with black and ruff"
	@echo "  clean                  Clean rpax artifacts"
	@echo "  clean-lake             Clean entire rpax lake (destructive)"
	@echo "  clean-build            Show command to clean Python build artifacts"
	@echo "  install                Install package in development mode"
	@echo "  ci-test                Run tests with coverage for CI"
	@echo "  build                  Build package distributions"
	@echo "  test-install           Test installation from built package"
	@echo "  check-package          Validate built package contents"
	@echo "  llm-context            Create LLM context zip with ADRs, TODO.md, and data model"

# Parse all test corpuses
.PHONY: parse-all-corpuses parse-all parse-all-legacy parse-all-v0
parse-all-legacy: parse-corpus-core1 parse-corpus-core10 parse-frozenchlorine parse-cprima-violation parse-cprima-noviolation
parse-all-v0: parse-v0-corpus-core1 parse-v0-corpus-core10 parse-v0-frozenchlorine parse-v0-cprima-violation parse-v0-cprima-noviolation
parse-all: parse-all-legacy parse-all-v0
parse-all-corpuses: parse-all

# Individual corpus parsing targets
.PHONY: parse-corpus-core1
parse-corpus-core1:
	@echo "Parsing c25v001_CORE_00000001 corpus..."
	$(RPAX) parse "$(CORPUS_CORE1)"

.PHONY: parse-corpus-core10  
parse-corpus-core10:
	@echo "Parsing c25v001_CORE_00000010 corpus..."
	$(RPAX) parse "$(CORPUS_CORE10)"

.PHONY: parse-frozenchlorine
parse-frozenchlorine:
	@echo "Parsing FrozenChlorine corpus..."
	$(RPAX) parse "$(CORPUS_FROZENCHLORINE)"

.PHONY: parse-cprima-violation
parse-cprima-violation:
	@echo "Parsing CPRIMA violation corpus..."
	$(RPAX) parse "$(CORPUS_CPRIMA_VIOLATION)"

.PHONY: parse-cprima-noviolation
parse-cprima-noviolation:
	@echo "Parsing CPRIMA no-violation corpus..."
	$(RPAX) parse "$(CORPUS_CPRIMA_NOVIOLATION)"

# V0 schema parsing targets
.PHONY: parse-v0-corpus-core1
parse-v0-corpus-core1:
	@echo "Parsing c25v001_CORE_00000001 corpus with v0 schema..."
	$(RPAX) parse "$(CORPUS_CORE1)" --schema v0

.PHONY: parse-v0-corpus-core10  
parse-v0-corpus-core10:
	@echo "Parsing c25v001_CORE_00000010 corpus with v0 schema..."
	$(RPAX) parse "$(CORPUS_CORE10)" --schema v0

.PHONY: parse-v0-frozenchlorine
parse-v0-frozenchlorine:
	@echo "Parsing FrozenChlorine corpus with v0 schema..."
	$(RPAX) parse "$(CORPUS_FROZENCHLORINE)" --schema v0

.PHONY: parse-v0-cprima-violation
parse-v0-cprima-violation:
	@echo "Parsing CPRIMA violation corpus with v0 schema..."
	$(RPAX) parse "$(CORPUS_CPRIMA_VIOLATION)" --schema v0

.PHONY: parse-v0-cprima-noviolation
parse-v0-cprima-noviolation:
	@echo "Parsing CPRIMA no-violation corpus with v0 schema..."
	$(RPAX) parse "$(CORPUS_CPRIMA_NOVIOLATION)" --schema v0

# Cross-project testing targets
.PHONY: test-projects
test-projects:
	@echo "Testing cross-project access commands..."
	@echo "Resolving projects with partial name 'CORE'..."
	$(RPAX) projects CORE --action resolve --path "$(RPAX_LAKE)"
	@echo ""
	@echo "Getting entry points for c25v001_CORE_00000001..."
	$(RPAX) projects c25v001_CORE_00000001 --action entry-points --path "$(RPAX_LAKE)"
	@echo ""
	@echo "Getting project summary for FrozenChlorine..."
	$(RPAX) projects FrozenChlorine --action summary --path "$(RPAX_LAKE)"

# Development targets (cross-platform using PowerShell Core)
.PHONY: test
test:
	$(PYTHON) -m pytest

.PHONY: lint
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy src/

.PHONY: format
format:
	$(PYTHON) -m black .
	$(PYTHON) -m ruff --fix .

.PHONY: clean
clean:
	$(RPAX) clear artifacts --confirm

.PHONY: clean-lake
clean-lake:
	$(RPAX) clear lake --confirm

.PHONY: clean-build
clean-build:
	@echo "Use 'uv build --clean' or 'rm -rf build/ dist/ *.egg-info/' to clean Python build artifacts"

.PHONY: install
install:
	$(PYTHON) -m pip install -e .[dev]

.PHONY: ci-test
ci-test:
	$(PYTHON) -m pytest --cov=rpax --cov-report=xml --cov-report=term-missing

.PHONY: build
build:
	$(PYTHON) -m build

.PHONY: test-install
test-install:
	@echo "Testing package installation from built wheel..."
	@if (Test-Path "dist/*.whl") { \
		$$wheelFile = Get-ChildItem "dist/*.whl" | Select-Object -First 1; \
		Write-Host "Installing $$($wheelFile.Name)..."; \
		pip install --force-reinstall "$$($wheelFile.FullName)"; \
		Write-Host "Testing installed package..."; \
		rpax --version; \
		rpax --help; \
		Write-Host "Package installation test completed successfully!"; \
	} else { \
		Write-Error "No wheel files found in dist/. Run 'make build' first."; \
		exit 1; \
	}

.PHONY: check-package
check-package:
	@echo "Checking built package contents..."
	@if (Test-Path "dist/*.whl") { \
		$$wheelFile = Get-ChildItem "dist/*.whl" | Select-Object -First 1; \
		Write-Host "Checking contents of $$($wheelFile.Name)..."; \
		$(PYTHON) -m zipfile -l "$$($wheelFile.FullName)"; \
		Write-Host "Validating package with twine..."; \
		$(PYTHON) -m twine check "dist/*"; \
	} else { \
		Write-Error "No wheel files found in dist/. Run 'make build' first."; \
		exit 1; \
	}

.PHONY: llm-context
llm-context:
	@pwsh -Command " \
		Write-Host 'Creating LLM context zip with ADRs, TODO.md, and data model...'; \
		New-Item -ItemType Directory -Force -Path 'docs/scratch' | Out-Null; \
		$$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'; \
		$$zipPath = \"docs/scratch/llm-context-$$timestamp.zip\"; \
		$$tempDir = 'docs/scratch/temp-context'; \
		New-Item -ItemType Directory -Force -Path $$tempDir | Out-Null; \
		Write-Host 'Collecting files...'; \
		Copy-Item 'docs/adr/ADR-*.md' $$tempDir -Force; \
		if (Test-Path 'docs/lake-data-model.md') { Copy-Item 'docs/lake-data-model.md' $$tempDir -Force }; \
		Copy-Item 'TODO.md' $$tempDir -Force; \
		if (Test-Path 'CHANGELOG.md') { Copy-Item 'CHANGELOG.md' $$tempDir -Force }; \
		Get-ChildItem 'docs/roadmap' -Recurse -File -Name '*.md' | ForEach-Object { \
			$$sourcePath = Join-Path 'docs/roadmap' $$_; \
			$$prefixedName = $$_ -replace '[/\\\\]', '-'; \
			$$destPath = Join-Path $$tempDir \"roadmap-$$prefixedName\"; \
			Copy-Item $$sourcePath $$destPath -Force; \
		}; \
		Write-Host \"Creating zip archive: $$zipPath\"; \
		Compress-Archive -Path \"$$tempDir/*\" -DestinationPath $$zipPath -Force; \
		Remove-Item -Recurse -Force $$tempDir; \
		$$zipSize = [math]::Round((Get-Item $$zipPath).Length / 1KB, 1); \
		Write-Host \"LLM context zip created: $$zipPath ($${zipSize}KB)\"; \
		Write-Host 'Contains: ADR files, TODO.md, CHANGELOG.md, lake data model, roadmap files'; \
		"