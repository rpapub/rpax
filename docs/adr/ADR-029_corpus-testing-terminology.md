# ADR-029: Corpus Projects and Aspects for Parser/Lake Validation

**Status:** Approved  
**Date:** 2025-09-06  
**Deciders:** System Architecture, Testing Strategy  
**Consulted:** Parser Layer, Validation Layer

## Context

The rpax parser and lake model must be validated against **real UiPath Studio projects**, not only synthetic unit tests. These projects serve as *external artifacts* that exercise specific parts of the data model (workflows, arguments, invocations, activities, errors).

Current ad-hoc testing approach lacks:
- Systematic coverage of parser edge cases
- Clear terminology for test artifacts
- Traceability between test inputs and data model features
- Reproducible validation across different environments

## Decision

Adopt the terms **Corpus Project** and **Aspect** for systematic coverage:

* **Corpus Project**: A curated UiPath Studio project used as input for parser validation
* **Aspect**: A defined feature or dimension of the rpax-lake data model that a corpus project is intended to cover (e.g., entrypoint handling, invocation resolution, activity trees)

## Rules

1. **Aspect Declaration**: Each corpus project must declare the **aspects** it covers in metadata
2. **Multi-Aspect Coverage**: A corpus project can cover multiple aspects simultaneously  
3. **Coverage Tracking**: Maintain traceability matrix ensuring all critical aspects are exercised
4. **Versioned Artifacts**: Corpus projects are versioned and stored with reproducible setup instructions
5. **Isolation**: Each corpus project should be self-contained and not depend on external resources

## Terminology

### Corpus Project
A real UiPath Studio project specifically selected or created for testing rpax parser functionality. Characteristics:
- Contains `project.json` and `.xaml` workflow files
- Represents realistic usage patterns from actual RPA development
- Includes both positive cases (valid structures) and negative cases (edge cases, malformed inputs)
- Documented with setup instructions and expected outcomes

### Aspect
A specific dimension of the rpax data model or parser behavior being validated:
- **Entrypoint Resolution**: How `Main.xaml` and entry workflows are identified
- **Invocation Chains**: Cross-workflow calls and argument passing
- **Activity Trees**: XAML parsing and activity hierarchy extraction
- **Error Handling**: Malformed XAML, missing files, circular references
- **Path Normalization**: Case sensitivity, relative paths, cross-platform compatibility
- **Large Scale**: Performance and memory usage with complex projects (1000+ workflows)

## Implementation

### Corpus Project Structure
```
corpus/
├── project-alpha/           # Corpus project name
│   ├── project.json        # UiPath project metadata
│   ├── Main.xaml           # Entry workflow
│   ├── workflows/          # Additional workflows
│   ├── .rpax.json          # rpax configuration
│   ├── corpus-metadata.json # Aspect declarations and expectations
│   └── README.md           # Setup and validation instructions
├── project-beta/
└── validation-matrix.json  # Coverage tracking
```

### Aspect Coverage Matrix
```json
{
  "aspects": {
    "entrypoint-resolution": ["project-alpha", "project-gamma"],
    "invocation-chains": ["project-alpha", "project-beta"],
    "activity-trees": ["project-alpha", "project-beta", "project-delta"],
    "error-handling": ["project-epsilon"],
    "large-scale": ["project-mega"]
  }
}
```

## Consequences

**Positive:**
- Clear terminology for discussing test artifacts and validation strategy
- Systematic approach to ensuring parser robustness across realistic inputs
- Traceability between test cases and data model features
- Reproducible validation process for CI/CD integration

**Negative:**
- Additional overhead in maintaining corpus projects and aspect mapping
- Requires discipline to keep corpus metadata synchronized with actual project contents
- Storage requirements for realistic UiPath projects in repository

**Neutral:**
- Establishes foundation for future automated validation pipelines
- Enables structured discussion of parser coverage gaps
- Compatible with existing unit test infrastructure

## Compliance

- **ADR-001**: Corpus projects validate XAML parsing resilience across real-world patterns
- **ADR-002**: Each layer (Parser, Validation) can define relevant aspects for testing
- **ADR-004**: Corpus projects include `.rpax.json` to test configuration handling

## Related ADRs

- **ADR-001**: XAML Parsing Strategy - corpus projects validate parsing resilience
- **ADR-002**: Layer Architecture - aspects map to specific layer responsibilities  
- **ADR-004**: Configuration Schema - corpus projects test config handling

## Future Work

- Automated corpus project discovery and validation in CI pipeline
- Aspect coverage reporting and gap analysis tooling
- Integration with performance benchmarking for large-scale aspects
- Community contribution guidelines for corpus project submissions