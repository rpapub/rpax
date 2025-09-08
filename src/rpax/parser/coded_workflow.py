"""Coded workflow parser for .cs files.

Parses UiPath coded workflows (C# classes) to extract workflow metadata,
arguments, dependencies, and other relevant information for integration
with the v0/ schema as first-class citizens.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class CodedWorkflowArgument:
    """Represents an argument in a coded workflow."""
    name: str
    type: str
    direction: str  # "in", "out", "in_out"
    default_value: Optional[str] = None
    description: Optional[str] = None


@dataclass  
class CodedWorkflowMethod:
    """Represents a method in a coded workflow."""
    name: str
    return_type: str
    parameters: List[CodedWorkflowArgument]
    is_execute: bool = False  # Whether this is the main Execute method
    body_summary: Optional[str] = None


@dataclass
class CodedWorkflowInfo:
    """Information extracted from a coded workflow .cs file."""
    class_name: str
    namespace: str
    base_class: Optional[str]
    using_statements: List[str]
    arguments: List[CodedWorkflowArgument]
    methods: List[CodedWorkflowMethod]
    dependencies: Set[str]  # Inferred package dependencies
    file_path: str
    relative_path: str
    

class CodedWorkflowParser:
    """Parser for UiPath coded workflows in C#."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_coded_workflow(self, file_path: Path, relative_path: str) -> Optional[CodedWorkflowInfo]:
        """Parse a coded workflow C# file.
        
        Args:
            file_path: Absolute path to the .cs file
            relative_path: Relative path from project root
            
        Returns:
            CodedWorkflowInfo if successfully parsed, None otherwise
        """
        try:
            if not file_path.exists():
                self.logger.warning(f"Coded workflow file not found: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._parse_cs_content(content, str(file_path), relative_path)
            
        except Exception as e:
            self.logger.error(f"Failed to parse coded workflow {file_path}: {e}")
            return None
    
    def _parse_cs_content(self, content: str, file_path: str, relative_path: str) -> Optional[CodedWorkflowInfo]:
        """Parse C# file content to extract workflow information."""
        
        # Extract using statements
        using_statements = self._extract_using_statements(content)
        
        # Extract namespace
        namespace = self._extract_namespace(content)
        
        # Extract class information
        class_info = self._extract_class_info(content)
        if not class_info:
            self.logger.warning(f"No class found in coded workflow: {file_path}")
            return None
        
        class_name, base_class = class_info
        
        # Extract methods
        methods = self._extract_methods(content)
        
        # Extract arguments from constructor or Execute method
        arguments = self._extract_arguments_from_methods(methods)
        
        # Infer dependencies from using statements and code content
        dependencies = self._infer_dependencies(using_statements, content)
        
        return CodedWorkflowInfo(
            class_name=class_name,
            namespace=namespace,
            base_class=base_class,
            using_statements=using_statements,
            arguments=arguments,
            methods=methods,
            dependencies=dependencies,
            file_path=file_path,
            relative_path=relative_path
        )
    
    def _extract_using_statements(self, content: str) -> List[str]:
        """Extract using statements from C# content."""
        using_pattern = r'using\s+([^;]+);'
        matches = re.findall(using_pattern, content)
        return [match.strip() for match in matches]
    
    def _extract_namespace(self, content: str) -> str:
        """Extract namespace from C# content."""
        namespace_pattern = r'namespace\s+([^\s\{]+)'
        match = re.search(namespace_pattern, content)
        return match.group(1) if match else ""
    
    def _extract_class_info(self, content: str) -> Optional[tuple[str, Optional[str]]]:
        """Extract class name and base class from C# content."""
        # Match class declaration with optional inheritance
        class_pattern = r'(?:public\s+)?class\s+(\w+)(?:\s*:\s*([^\{]+))?'
        match = re.search(class_pattern, content)
        
        if match:
            class_name = match.group(1)
            base_class = match.group(2).strip() if match.group(2) else None
            return class_name, base_class
        
        return None
    
    def _extract_methods(self, content: str) -> List[CodedWorkflowMethod]:
        """Extract method information from C# content."""
        methods = []
        
        # Pattern to match method declarations
        method_pattern = r'(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*\{'
        
        for match in re.finditer(method_pattern, content):
            return_type = match.group(1)
            method_name = match.group(2)
            params_str = match.group(3)
            
            # Parse parameters
            parameters = self._parse_method_parameters(params_str)
            
            # Check if this is the Execute method (main workflow method)
            is_execute = method_name.lower() == 'execute'
            
            methods.append(CodedWorkflowMethod(
                name=method_name,
                return_type=return_type,
                parameters=parameters,
                is_execute=is_execute
            ))
        
        return methods
    
    def _parse_method_parameters(self, params_str: str) -> List[CodedWorkflowArgument]:
        """Parse method parameter string into arguments."""
        parameters = []
        
        if not params_str.strip():
            return parameters
        
        # Split parameters by comma, handling generic types
        param_parts = self._split_parameters(params_str)
        
        for param in param_parts:
            param = param.strip()
            if not param:
                continue
            
            # Parse parameter: [direction] type name [= default]
            param_info = self._parse_single_parameter(param)
            if param_info:
                parameters.append(param_info)
        
        return parameters
    
    def _split_parameters(self, params_str: str) -> List[str]:
        """Split parameter string by commas, respecting generic type brackets."""
        parts = []
        current = ""
        bracket_depth = 0
        
        for char in params_str:
            if char == '<':
                bracket_depth += 1
            elif char == '>':
                bracket_depth -= 1
            elif char == ',' and bracket_depth == 0:
                parts.append(current)
                current = ""
                continue
            
            current += char
        
        if current:
            parts.append(current)
        
        return parts
    
    def _parse_single_parameter(self, param: str) -> Optional[CodedWorkflowArgument]:
        """Parse a single parameter string."""
        param = param.strip()
        
        # Handle parameter direction (out, ref, in)
        direction = "in"  # default
        if param.startswith('out '):
            direction = "out"
            param = param[4:].strip()
        elif param.startswith('ref '):
            direction = "in_out"
            param = param[4:].strip()
        elif param.startswith('in '):
            direction = "in"
            param = param[3:].strip()
        
        # Split into type and name (with optional default value)
        parts = param.split('=', 1)
        type_and_name = parts[0].strip()
        default_value = parts[1].strip() if len(parts) > 1 else None
        
        # Extract type and parameter name
        tokens = type_and_name.split()
        if len(tokens) >= 2:
            # Join all but last token as type (handles generic types)
            param_type = ' '.join(tokens[:-1])
            param_name = tokens[-1]
            
            return CodedWorkflowArgument(
                name=param_name,
                type=param_type,
                direction=direction,
                default_value=default_value
            )
        
        return None
    
    def _extract_arguments_from_methods(self, methods: List[CodedWorkflowMethod]) -> List[CodedWorkflowArgument]:
        """Extract workflow arguments from constructor or Execute method."""
        # Look for Execute method first
        for method in methods:
            if method.is_execute:
                return method.parameters
        
        # If no Execute method, look for constructor
        for method in methods:
            if method.name in ['Constructor', '__init__']:
                return method.parameters
        
        # Return parameters from first public method
        for method in methods:
            if method.parameters:
                return method.parameters
        
        return []
    
    def _infer_dependencies(self, using_statements: List[str], content: str) -> Set[str]:
        """Infer package dependencies from using statements and content."""
        dependencies = set()
        
        # Add dependencies based on using statements
        for using in using_statements:
            if using.startswith('UiPath.'):
                # Extract UiPath package name
                parts = using.split('.')
                if len(parts) >= 2:
                    package = f"{parts[0]}.{parts[1]}"
                    dependencies.add(package)
            elif using in ['System', 'System.Collections.Generic', 'System.Linq', 'System.Threading.Tasks']:
                # Standard .NET dependencies
                dependencies.add('System')
        
        # Scan content for UiPath activity usage
        uipath_patterns = [
            r'UiPath\.(\w+)\.',  # UiPath.Core.Activities usage
            r'Activities\.(\w+)',  # Activities usage
        ]
        
        for pattern in uipath_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                dependencies.add(f"UiPath.{match}")
        
        return dependencies


def discover_coded_workflows(project_root: Path, exclude_patterns: List[str] = None) -> List[Path]:
    """Discover all coded workflow .cs files in a project.
    
    Args:
        project_root: Root directory of the UiPath project
        exclude_patterns: List of glob patterns to exclude
        
    Returns:
        List of paths to coded workflow .cs files
    """
    if exclude_patterns is None:
        exclude_patterns = []
    
    coded_workflows = []
    
    # Look in common coded workflow directories
    coded_dirs = [
        project_root / ".codedworkflows",
        project_root / "CodedWorkflows", 
        project_root / "Workflows",
        project_root  # Also check root directory
    ]
    
    for coded_dir in coded_dirs:
        if coded_dir.exists() and coded_dir.is_dir():
            for cs_file in coded_dir.rglob("*.cs"):
                # Skip if matches exclude patterns
                if any(cs_file.match(pattern) for pattern in exclude_patterns):
                    continue
                
                # Skip obvious non-workflow files
                if any(skip in cs_file.name.lower() for skip in [
                    'assemblyinfo', 'globalusings', 'program.cs', 'startup.cs'
                ]):
                    continue
                
                coded_workflows.append(cs_file)
    
    return coded_workflows