"""Constants and configuration for XAML parsing.

All namespace definitions, blacklists, and parsing patterns
centralized for easy maintenance.
"""

from typing import Dict, Set

# Standard XAML namespaces used in workflow automation
STANDARD_NAMESPACES: Dict[str, str] = {
    'x': 'http://schemas.microsoft.com/winfx/2006/xaml',
    'activities': 'http://schemas.microsoft.com/netfx/2009/xaml/activities',
    'sap': 'http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation',
    'sap2010': 'http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation',
    'ui': 'http://schemas.uipath.com/workflow/activities',
    'scg': 'clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib',
    'sco': 'clr-namespace:System.Collections.ObjectModel;assembly=System.Private.CoreLib',
    'snm': 'clr-namespace:System.Net.Mail;assembly=System.Net.Mail',
    'sd': 'clr-namespace:System.Data;assembly=System.Data.Common',
    'ss': 'clr-namespace:System.Security;assembly=System.Private.CoreLib'
}

# Elements to skip during activity parsing (metadata, not workflow logic)
SKIP_ELEMENTS: Set[str] = {
    # XAML structure elements
    'Members', 'Variables', 'Arguments', 'Imports',
    'NamespacesForImplementation', 'ReferencesForImplementation',
    'TextExpression', 'VisualBasic', 'Collection', 'AssemblyReference',
    
    # ViewState and presentation
    'ViewState', 'WorkflowViewState', 'WorkflowViewStateService',
    'VirtualizedContainerService', 'Annotation', 'HintSize', 'IdRef',
    
    # Property containers (handle separately)
    'Property', 'ActivityAction', 'DelegateInArgument', 'DelegateOutArgument',
    'InArgument', 'OutArgument', 'InOutArgument',
    
    # Container sub-elements
    'Then', 'Else', 'Catches', 'Catch', 'Finally', 'States', 'Transitions',
    'Body', 'Handler', 'Condition', 'Default', 'Case',
    
    # Technical metadata
    'Dictionary', 'Boolean', 'String', 'Int32', 'Double',
    'AssignOperation', 'BackupSlot', 'BackupValues'
}

# Activity elements that are always considered visual/workflow logic
CORE_VISUAL_ACTIVITIES: Set[str] = {
    # Control flow
    'Sequence', 'Flowchart', 'StateMachine', 'TryCatch', 'Parallel',
    'ParallelForEach', 'ForEach', 'While', 'DoWhile', 'If', 'Switch',
    
    # Workflow operations
    'InvokeWorkflowFile', 'Assign', 'Delay', 'RetryScope',
    'Pick', 'PickBranch', 'MultipleAssign',
    
    # Common activities (logging, user interaction)
    'LogMessage', 'WriteLine', 'InputDialog', 'MessageBox',
    
    # Method calls
    'InvokeMethod', 'InvokeCode'
}

# Attribute patterns that indicate invisible/technical properties
INVISIBLE_ATTRIBUTE_PATTERNS: Set[str] = {
    'VirtualizedContainerService.HintSize',
    'WorkflowViewState.IdRef', 
    'Annotation.AnnotationText',  # This is visible content but stored as invisible attribute
    'WorkflowViewStateService.ViewState'
}

# Standard argument direction mappings
ARGUMENT_DIRECTIONS: Dict[str, str] = {
    'InArgument': 'in',
    'OutArgument': 'out', 
    'InOutArgument': 'inout'
}

# Expression patterns for detection
EXPRESSION_PATTERNS: Set[str] = {
    '[', ']',           # VB.NET expressions in brackets
    'New ', 'new ',     # Object creation
    'Function(', 'function(',  # VB.NET lambdas
    '(x) => ', '(x)=>',        # C# lambdas
    '.ToString()', '.ToLower()', '.ToUpper()',  # Common method calls
    'String.Format', 'Path.Combine', 'If(',     # Common functions
    '.Where(', '.Select(', '.OrderBy(',         # LINQ methods
}

# Common ViewState properties
VIEWSTATE_PROPERTIES: Set[str] = {
    'IsExpanded', 'IsPinned', 'IsAnnotationDocked',
    'IsEnabled', 'IsVisible', 'IsSelected'
}

# Default extraction settings
DEFAULT_CONFIG = {
    'extract_arguments': True,
    'extract_variables': True, 
    'extract_activities': True,
    'extract_expressions': True,
    'extract_viewstate': True,
    'extract_namespaces': True,
    'extract_assembly_references': True,
    'preserve_raw_metadata': True,
    'strict_mode': False,           # Continue parsing on errors
    'max_depth': 100,               # Prevent infinite recursion
    'expression_language': 'VisualBasic'
}