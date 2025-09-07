# XAML Parser

Standalone XAML workflow parser for automation projects with zero external dependencies.

## Features

- **Complete metadata extraction** from XAML workflow files
- **Arguments** with types, directions, and annotations
- **Variables** from all workflow scopes
- **Activities** with full property analysis (visible and invisible)
- **Annotations** and documentation text
- **Expressions** with language detection
- **Zero dependencies** - uses only Python standard library
- **Graceful error handling** with detailed error reporting

## Installation

As a standalone package (when published):
```bash
pip install xaml-parser
```

For development within rpax project:
```python
from xaml_parser import XamlParser
```

## Quick Start

```python
from pathlib import Path
from xaml_parser import XamlParser

# Parse a workflow file
parser = XamlParser()
result = parser.parse_file(Path("workflow.xaml"))

if result.success:
    content = result.content
    print(f"Workflow: {content.root_annotation}")
    print(f"Arguments: {len(content.arguments)}")
    print(f"Activities: {len(content.activities)}")
    
    # Access arguments
    for arg in content.arguments:
        print(f"  {arg.direction} {arg.name}: {arg.type}")
        if arg.annotation:
            print(f"    -> {arg.annotation}")
    
    # Access activities with annotations
    for activity in content.activities:
        if activity.annotation:
            print(f"{activity.tag}: {activity.annotation}")
else:
    print("Parsing failed:", result.errors)
```

## Advanced Usage

### Custom Configuration

```python
config = {
    'extract_expressions': True,
    'extract_viewstate': False,
    'strict_mode': False,
    'max_depth': 50
}

parser = XamlParser(config)
result = parser.parse_file(file_path)
```

### Specialized Extractors

```python
from xaml_parser import ArgumentExtractor, ActivityExtractor

# Use specialized extractors directly
root = ET.fromstring(xaml_content)
namespaces = {'x': 'http://schemas.microsoft.com/winfx/2006/xaml'}

arguments = ArgumentExtractor.extract_arguments(root, namespaces)
```

## Data Models

### WorkflowContent
Main result containing all extracted metadata:
- `arguments`: List of WorkflowArgument objects
- `variables`: List of WorkflowVariable objects  
- `activities`: List of ActivityContent objects
- `root_annotation`: Main workflow description
- `namespaces`: XML namespace mappings
- `expression_language`: VB.NET or C#

### WorkflowArgument
Workflow parameter definition:
- `name`: Argument name
- `type`: Full .NET type signature
- `direction`: 'in', 'out', or 'inout'
- `annotation`: Documentation text
- `default_value`: Default value expression

### ActivityContent
Complete activity representation:
- `tag`: Activity type (Sequence, LogMessage, etc.)
- `display_name`: User-friendly name
- `annotation`: Business logic description
- `visible_attributes`: User-configured properties
- `invisible_attributes`: Technical ViewState data
- `configuration`: Nested element structure
- `expressions`: All expressions in activity

## Supported Features

### UiPath XAML Elements
- **Arguments**: InArgument, OutArgument, InOutArgument with annotations
- **Variables**: All scoped variables with types and defaults
- **Activities**: Complete activity tree with properties
- **Annotations**: Business logic documentation on all elements
- **Expressions**: VB.NET and C# expressions with LINQ, lambdas, method calls
- **ViewState**: UI metadata for studio presentation
- **Assembly References**: External library dependencies

### Error Handling
- Graceful degradation on malformed XAML
- Detailed error reporting with line numbers
- Continues parsing on non-critical errors
- Validates data quality and completeness

## Architecture

The parser is designed for modularity and reusability:

- `parser.py`: Main XamlParser class
- `models.py`: Data models using dataclasses (no external deps)  
- `extractors.py`: Specialized extraction logic
- `constants.py`: Configuration and patterns
- `utils.py`: Helper functions and validation

## Contributing

This package is part of the rpax project but designed for standalone use.
See the main rpax repository for contribution guidelines.

## License

MIT License - see LICENSE file for details.