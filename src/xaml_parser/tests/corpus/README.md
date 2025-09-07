# Test Corpus for XAML Parser

This directory contains test data organized into realistic project structures for comprehensive testing of the XAML parser package.

## Structure

```
corpus/
├── README.md                    # This file
├── simple_project/             # Basic project with minimal workflows
│   ├── project.json            # UiPath project configuration
│   ├── Main.xaml               # Simple main workflow
│   └── workflows/              # Additional workflows
│       ├── GetConfig.xaml      # Workflow with arguments
│       └── ProcessData.xaml    # Workflow with variables and activities
├── complex_project/            # Complex project with advanced features
│   ├── project.json            # Complex project configuration
│   ├── Main.xaml               # Main workflow with invocations
│   ├── Framework/              # Framework workflows
│   │   ├── InitAllSettings.xaml # Multi-argument workflow
│   │   └── CloseApplications.xaml
│   └── BusinessLogic/          # Business logic workflows
│       ├── ProcessInvoice.xaml
│       └── ValidateData.xaml
├── edge_cases/                 # Edge cases and error conditions
│   ├── malformed.xaml          # Malformed XML for error testing
│   ├── empty.xaml              # Empty workflow
│   ├── large_workflow.xaml     # Large workflow for performance testing
│   └── encoding_test.xaml      # Different encodings
└── future/                     # Reserved for future test data
    ├── coded_workflows/        # Code-based workflows (C#/VB.NET)
    └── object_repository/      # Object repository files
```

## Test Scenarios Covered

### Simple Project
- **Arguments**: Input/output parameters with annotations
- **Variables**: Workflow and activity-scoped variables  
- **Basic Activities**: Sequence, LogMessage, Assign, If/Else
- **Annotations**: Root and activity-level documentation

### Complex Project
- **Multi-file structure**: Realistic enterprise project layout
- **Workflow invocations**: InvokeWorkflowFile activities
- **Framework patterns**: Settings initialization, cleanup workflows
- **Business logic separation**: Clear separation of concerns
- **Complex expressions**: VB.NET/C# expressions with LINQ
- **Multiple namespaces**: Various UiPath activity packages

### Edge Cases
- **Error handling**: Malformed XML, encoding issues
- **Performance**: Large workflows with many activities
- **Empty states**: Minimal workflows, missing elements
- **Encoding variations**: UTF-8, UTF-16, BOM handling

## Usage in Tests

Test files can reference corpus data using:

```python
from pathlib import Path

# Get corpus directory
corpus_dir = Path(__file__).parent / "corpus"

# Test specific project
simple_project = corpus_dir / "simple_project"
main_workflow = simple_project / "Main.xaml"

# Run parser tests
parser = XamlParser()
result = parser.parse_file(main_workflow)
```

## Golden Freezes

This corpus serves as "golden freezes" test data - stable reference implementations that validate:

1. **Parsing accuracy**: Complete metadata extraction
2. **Schema compliance**: Strict output validation  
3. **Performance benchmarks**: Consistent timing expectations
4. **Error handling**: Graceful degradation patterns
5. **Cross-platform consistency**: Same results across environments

## Future Extensions

The corpus is designed for extensibility:

- **Coded workflows**: UiPath workflows with embedded C#/VB.NET code
- **Object repository**: UI element definitions and selectors
- **Library projects**: Reusable workflow components
- **Modern activities**: Latest UiPath activity packages
- **Integration scenarios**: API calls, database operations, file processing