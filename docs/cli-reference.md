# rpax CLI Command Reference

**Version**: 0.0.1  
**Generated**: 2025-09-06 07:46:37  
**Generator**: CLI help output parsing

This document provides comprehensive reference for all rpax CLI commands, options, and usage patterns.

## Overview

Code-first CLI tool for UiPath project analysis +- Options -------------------------------------------------------------------+ | --version  -v        Show version and exit                                  | | --help               Show this message and exit.                            | +-----------------------------------------------------------------------------+ +- Commands ------------------------------------------------------------------+ | parse        Parse UiPath project(s) and generate artifacts.                | | list         List project elements with enhanced filtering, sorting, and    | |              output formats.                                                | | validate     Run validation rules on parser artifacts.                      | | graph        Generate workflow call graphs and diagrams.                    | | explain      Show detailed information about a specific workflow.           | | schema       Generate JSON schemas or validate artifacts against schemas.   | | help         Show detailed help information.                                | | activities   Access workflow activity trees, control flow, and resource     | |              references.                                                    | | projects     List all projects in the rpax lake.                            | | clear        Clear rpax lake data with strong safety guardrails.            | | pseudocode   Show pseudocode representation of workflow activities.         | +-----------------------------------------------------------------------------+

## Main Command

### `rpax`

**Usage**: `rpax [OPTIONS] COMMAND [ARGS]...`

Code-first CLI tool for UiPath project analysis +- Options -------------------------------------------------------------------+ | --version  -v        Show version and exit                                  | | --help               Show this message and exit.                            | +-----------------------------------------------------------------------------+ +- Commands ------------------------------------------------------------------+ | parse        Parse UiPath project(s) and generate artifacts.                | | list         List project elements with enhanced filtering, sorting, and    | |              output formats.                                                | | validate     Run validation rules on parser artifacts.                      | | graph        Generate workflow call graphs and diagrams.                    | | explain      Show detailed information about a specific workflow.           | | schema       Generate JSON schemas or validate artifacts against schemas.   | | help         Show detailed help information.                                | | activities   Access workflow activity trees, control flow, and resource     | |              references.                                                    | | projects     List all projects in the rpax lake.                            | | clear        Clear rpax lake data with strong safety guardrails.            | | pseudocode   Show pseudocode representation of workflow activities.         | +-----------------------------------------------------------------------------+


## Generated Documentation Metadata

- **rpax version**: 0.0.1
- **Documentation generated**: 2025-09-06T07:46:37.903922
- **Generator method**: CLI help output parsing
- **Commands documented**: 1

## Usage Examples

### Basic Project Parsing
```bash
rpax parse /path/to/uipath/project
```

### View Available Projects
```bash  
rpax list --lake-path /path/to/.rpax-lake
```

### Generate Pseudocode
```bash
rpax pseudocode --project my-project-slug WorkflowName.xaml
```

### Show All Workflows  
```bash
rpax pseudocode --project my-project-slug --all
```

For more detailed examples and advanced usage, see the main rpax documentation.
