# XAML Parser Test Data Corpus

This directory contains curated XAML test files for comprehensive testing of the `xaml_parser` package without external dependencies.

## Test Files

### `simple_sequence.xaml`
- **Purpose**: Basic sequence with variables, assignments, logging, and conditional logic
- **Key Activities**: Sequence, Assign, LogMessage, If
- **Business Logic**: Variable manipulation, conditional execution
- **Expected Activity Count**: 5 activities
- **Variables**: testMessage (String), counter (Int32)

### `ui_automation_sample.xaml`
- **Purpose**: UI automation activities with selectors and target elements
- **Key Activities**: Click, TypeInto, ElementExists
- **Business Logic**: Web form interaction with selectors
- **Expected Activity Count**: 6 activities
- **Selectors**: Button, Input field, Submit button
- **Variables**: inputText (String), elementExists (Boolean)

### `complex_workflow.xaml`
- **Purpose**: Complex nested structures with loops, error handling, and branching logic
- **Key Activities**: TryCatch, ForEach, Switch, nested Sequences
- **Business Logic**: List processing with type-specific handling
- **Expected Activity Count**: 15+ activities
- **Variables**: itemList (List), currentItem (String), itemCount (Int32), processComplete (Boolean)

### `invoke_workflows_sample.xaml`
- **Purpose**: Workflow invocations with argument passing
- **Key Activities**: InvokeWorkflowFile with various argument patterns
- **Business Logic**: Framework/Process separation pattern
- **Expected Activity Count**: 8 activities
- **Invoked Workflows**: Framework\ValidateInput.xaml, Process\ProcessData.xaml, Framework\HandleError.xaml
- **Variables**: result1 (String), result2 (Int32), success (Boolean)

## Usage in Tests

These files are designed to be used with the golden freeze test system:

```python
from xaml_parser.parser import XamlParser
from pathlib import Path

test_data_dir = Path(__file__).parent / "test_data"
simple_xaml = test_data_dir / "simple_sequence.xaml"

parser = XamlParser()
result = parser.parse_file(simple_xaml)
```

## Golden Results Structure

Each test file should have corresponding golden results that capture:
- Total activity count
- Activity type distribution 
- Key activity properties (DisplayName, arguments, etc.)
- Variable definitions and references
- Expression patterns
- Selector patterns (for UI activities)

## Test Coverage

This corpus provides coverage for:
- ✅ Basic activity types (Assign, LogMessage, If)
- ✅ UI automation activities (Click, TypeInto, ElementExists) 
- ✅ Control flow (ForEach, Switch, TryCatch)
- ✅ Workflow invocations (InvokeWorkflowFile)
- ✅ Variable definitions and references
- ✅ Expression extraction
- ✅ Selector parsing
- ✅ Nested structures and complex hierarchies
- ✅ Error handling patterns
- ✅ Annotation extraction

## Maintenance

When adding new test files:
1. Include comprehensive business logic examples
2. Add expected activity counts to this README
3. Ensure new patterns are covered by golden freeze tests
4. Keep files focused on specific test scenarios
5. Document key activities and variables for reference