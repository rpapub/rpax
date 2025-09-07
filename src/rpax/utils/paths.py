"""Path normalization utilities for cross-platform compatibility."""


def normalize_path(path: str) -> str:
    """Convert any path to canonical forward slash format.
    
    This function normalizes Windows backslashes to POSIX forward slashes
    for consistent internal representation per ADR-030.
    
    Args:
        path: Path with any separator format
        
    Returns:
        Path with forward slashes only
        
    Examples:
        >>> normalize_path("Framework\\InitAllSettings.xaml")
        'Framework/InitAllSettings.xaml'
        >>> normalize_path("Framework/InitAllSettings.xaml")  
        'Framework/InitAllSettings.xaml'
        >>> normalize_path("C:\\Projects\\MyWorkflow.xaml")
        'C:/Projects/MyWorkflow.xaml'
    """
    if not path:
        return path
    
    return path.replace("\\", "/")


def normalize_workflow_path(target_path: str) -> str:
    """Normalize workflow target path for consistent resolution.
    
    Handles both relative and absolute paths, ensuring forward slash format
    for internal usage while preserving path structure.
    
    Args:
        target_path: Workflow path from InvokeWorkflowFile or similar
        
    Returns:
        Normalized path with forward slashes
    """
    if not target_path:
        return target_path
        
    # Remove .xaml extension if present for ID matching
    normalized = normalize_path(target_path)
    if normalized.endswith(".xaml"):
        normalized = normalized[:-5]  # Remove ".xaml"
        
    return normalized