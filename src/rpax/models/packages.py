"""Models for UiPath package analysis and dependency tracking."""

from typing import Dict, List, Set
from pydantic import BaseModel, Field


class PackageUsage(BaseModel):
    """Package usage analysis for a single workflow."""
    workflow_id: str = Field(alias="workflowId")
    namespaces: Dict[str, str] = Field(default_factory=dict)  # prefix -> namespace URI
    packages_used: List[str] = Field(alias="packagesUsed", default_factory=list)
    namespace_count: int = Field(alias="namespaceCount", default=0)
    package_count: int = Field(alias="packageCount", default=0)

    model_config = {"populate_by_name": True}


class PackageReference(BaseModel):
    """Individual package reference with metadata."""
    package_name: str = Field(alias="packageName")
    version: str | None = None
    namespace_uris: List[str] = Field(alias="namespaceUris", default_factory=list)
    used_in_workflows: List[str] = Field(alias="usedInWorkflows", default_factory=list)
    is_declared: bool = Field(alias="isDeclared", default=False)  # In project.json dependencies
    is_used: bool = Field(alias="isUsed", default=False)  # Found in XAML namespaces
    
    model_config = {"populate_by_name": True}


class ProjectPackageAnalysis(BaseModel):
    """Complete package analysis for a UiPath project."""
    project_slug: str = Field(alias="projectSlug")
    project_name: str = Field(alias="projectName") 
    analyzed_at: str = Field(alias="analyzedAt")  # ISO timestamp
    
    # Package inventory
    declared_dependencies: Dict[str, str] = Field(alias="declaredDependencies", default_factory=dict)  # package -> version from project.json
    packages: List[PackageReference] = Field(default_factory=list)  # All package references
    
    # Usage statistics
    total_packages_declared: int = Field(alias="totalPackagesDeclared", default=0)
    total_packages_used: int = Field(alias="totalPackagesUsed", default=0)
    total_workflows_analyzed: int = Field(alias="totalWorkflowsAnalyzed", default=0)
    
    # Analysis results
    unused_packages: List[str] = Field(alias="unusedPackages", default_factory=list)  # Declared but not used
    undeclared_packages: List[str] = Field(alias="undeclaredPackages", default_factory=list)  # Used but not declared
    
    @property
    def package_usage_ratio(self) -> float:
        """Calculate ratio of used vs declared packages."""
        if self.total_packages_declared == 0:
            return 1.0 if self.total_packages_used == 0 else 0.0
        return self.total_packages_used / self.total_packages_declared
    
    @property
    def has_unused_packages(self) -> bool:
        """Check if project has unused declared packages."""
        return len(self.unused_packages) > 0
    
    @property
    def has_undeclared_packages(self) -> bool:
        """Check if project uses undeclared packages."""
        return len(self.undeclared_packages) > 0

    model_config = {"populate_by_name": True}


def analyze_package_usage(
    declared_dependencies: Dict[str, str],
    workflow_packages: Dict[str, List[str]]
) -> ProjectPackageAnalysis:
    """Analyze package usage across project workflows.
    
    Args:
        declared_dependencies: Dependencies from project.json
        workflow_packages: Map of workflow_id -> list of used packages
        
    Returns:
        Complete package analysis
    """
    from datetime import UTC, datetime
    
    # Build comprehensive package reference list
    all_declared = set(declared_dependencies.keys())
    all_used = set()
    package_to_workflows = {}
    
    # Collect all used packages and track workflow usage
    for workflow_id, packages in workflow_packages.items():
        for package in packages:
            all_used.add(package)
            if package not in package_to_workflows:
                package_to_workflows[package] = []
            package_to_workflows[package].append(workflow_id)
    
    # Build package reference objects
    packages = []
    all_packages = all_declared | all_used
    
    for package_name in sorted(all_packages):
        version = declared_dependencies.get(package_name)
        used_in_workflows = package_to_workflows.get(package_name, [])
        
        packages.append(PackageReference(
            package_name=package_name,
            version=version,
            used_in_workflows=used_in_workflows,
            is_declared=package_name in all_declared,
            is_used=package_name in all_used
        ))
    
    # Identify unused and undeclared packages
    unused_packages = sorted(all_declared - all_used)
    undeclared_packages = sorted(all_used - all_declared)
    
    return ProjectPackageAnalysis(
        project_slug="",  # Will be filled by caller
        project_name="",  # Will be filled by caller
        analyzed_at=datetime.now(UTC).isoformat(),
        declared_dependencies=declared_dependencies,
        packages=packages,
        total_packages_declared=len(all_declared),
        total_packages_used=len(all_used),
        total_workflows_analyzed=len(workflow_packages),
        unused_packages=unused_packages,
        undeclared_packages=undeclared_packages
    )