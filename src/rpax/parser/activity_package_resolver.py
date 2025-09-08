"""
Activity Package Resolver for mapping activity types to their source packages.

Maps UiPath activity types (Assign, InvokeWorkflowFile, etc.) to their NuGet package sources
with classification information (vendor_official, custom_local, third_party).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from rpax.parser.dependency_classifier import DependencyClassifier, DependencyInfo, DependencyType


@dataclass
class PackageSourceInfo:
    """Package source information for an activity."""
    package_name: str
    package_version: str | None = None
    classification: str | None = None  # vendor_official, custom_local, third_party
    assembly: str | None = None


@dataclass 
class PackageInfo:
    """Internal package mapping information."""
    package_name: str
    assembly_name: str


class ActivityPackageResolver:
    """Resolves activity types to their source packages."""
    
    def __init__(self, dependencies: List[DependencyInfo], classifier: DependencyClassifier):
        self.dependencies = dependencies
        self.classifier = classifier
        self.activity_catalog = self._build_activity_catalog()
    
    def _build_activity_catalog(self) -> Dict[str, PackageInfo]:
        """Build mapping of activity_type → package info."""
        catalog = {}
        
        # Known UiPath System Activities
        catalog.update({
            # Core workflow control activities
            "Assign": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "InvokeWorkflowFile": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "Sequence": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "If": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "TryCatch": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "Parallel": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "Pick": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "Switch": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "ForEach": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "While": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            "DoWhile": PackageInfo("UiPath.System.Activities", "UiPath.Core.Activities.dll"),
            
            # System activities
            "LogMessage": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "WriteLine": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "MessageBox": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "Delay": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "TerminateWorkflow": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            
            # File system activities
            "ReadTextFile": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "WriteTextFile": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "FileExists": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "DirectoryExists": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "CreateDirectory": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "DeleteFile": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "CopyFile": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "MoveFile": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            
            # Data handling activities
            "DeserializeJson": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "SerializeJson": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "BuildDataTable": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "AddDataRow": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "GetRowItem": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            
            # Web activities (common ones in System.Activities)
            "HttpClient": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
            "HttpRequest": PackageInfo("UiPath.System.Activities", "UiPath.System.Activities.dll"),
        })
        
        # UI Automation activities (separate package)
        ui_activities = {
            "Click": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
            "Type": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
            "GetText": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
            "GetAttribute": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
            "FindElement": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
            "WaitElement": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
            "ElementExists": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
            "HighlightElement": PackageInfo("UiPath.UIAutomation.Activities", "UiPath.UIAutomation.Activities.dll"),
        }
        catalog.update(ui_activities)
        
        # Excel activities
        excel_activities = {
            "ExcelReadRange": PackageInfo("UiPath.Excel.Activities", "UiPath.Excel.Activities.dll"),
            "ExcelWriteRange": PackageInfo("UiPath.Excel.Activities", "UiPath.Excel.Activities.dll"),
            "ExcelOpenWorkbook": PackageInfo("UiPath.Excel.Activities", "UiPath.Excel.Activities.dll"),
            "ExcelCloseWorkbook": PackageInfo("UiPath.Excel.Activities", "UiPath.Excel.Activities.dll"),
            "ExcelCreatePivotTable": PackageInfo("UiPath.Excel.Activities", "UiPath.Excel.Activities.dll"),
        }
        catalog.update(excel_activities)
        
        # Mail activities
        mail_activities = {
            "SendOutlookMail": PackageInfo("UiPath.Mail.Activities", "UiPath.Mail.Activities.dll"),
            "GetOutlookMail": PackageInfo("UiPath.Mail.Activities", "UiPath.Mail.Activities.dll"),
            "SendMail": PackageInfo("UiPath.Mail.Activities", "UiPath.Mail.Activities.dll"),
            "GetMail": PackageInfo("UiPath.Mail.Activities", "UiPath.Mail.Activities.dll"),
        }
        catalog.update(mail_activities)
        
        # Custom activities from project dependencies
        for dep in self.dependencies:
            if dep.classification == DependencyType.CUSTOM_LOCAL:
                # For custom local activities, we'd need to analyze the assemblies
                # For now, we'll create placeholder entries based on the package name
                # In a full implementation, this would scan the actual DLL files
                pass
        
        return catalog
    
    def resolve_activity_package(self, activity_type: str) -> Optional[PackageSourceInfo]:
        """Resolve activity type to package source information."""
        if activity_type in self.activity_catalog:
            package_info = self.activity_catalog[activity_type]
            
            # Find version and classification from project dependencies
            package_version = None
            package_classification = None
            for dep in self.dependencies:
                if dep.name == package_info.package_name:
                    package_version = dep.version
                    package_classification = dep.classification.value
                    break
            
            # Default classification for known UiPath packages
            if package_classification is None:
                if package_info.package_name.startswith("UiPath."):
                    package_classification = "vendor_official"
                else:
                    package_classification = "third_party"
            
            return PackageSourceInfo(
                package_name=package_info.package_name,
                package_version=package_version,
                classification=package_classification,
                assembly=package_info.assembly_name
            )
        
        # Unknown activity type - try to infer from naming patterns
        return self._infer_package_from_activity_name(activity_type)
    
    def _infer_package_from_activity_name(self, activity_type: str) -> Optional[PackageSourceInfo]:
        """Attempt to infer package source from activity name patterns."""
        
        # Check for custom activity naming patterns
        # Many custom activities follow naming conventions like:
        # - CompanyName.ActivityName
        # - ProjectName_ActivityName
        # - Custom.Library.ActivityName
        
        if "." in activity_type:
            # Likely a custom activity with namespace
            parts = activity_type.split(".")
            if len(parts) >= 2:
                potential_package = ".".join(parts[:-1])  # All but last part
                
                # Check if we have this package in dependencies
                for dep in self.dependencies:
                    if dep.name == potential_package:
                        return PackageSourceInfo(
                            package_name=dep.name,
                            package_version=dep.version,
                            classification=dep.classification.value,
                            assembly=f"{potential_package}.dll"
                        )
        
        # Check for activities from known packages in dependencies
        for dep in self.dependencies:
            # Some heuristics for matching activities to packages
            if dep.classification == DependencyType.CUSTOM_LOCAL:
                # Custom activities might match package name patterns
                package_base = dep.name.replace(".", "").lower()
                activity_lower = activity_type.lower()
                
                if package_base in activity_lower or activity_lower.startswith(package_base[:5]):
                    return PackageSourceInfo(
                        package_name=dep.name,
                        package_version=dep.version,
                        classification=dep.classification.value,
                        assembly=f"{dep.name}.dll"
                    )
        
        # Unable to resolve - return None
        return None
    
    def get_package_activity_catalog(self, package_name: str) -> List[str]:
        """Get all activity types provided by a specific package."""
        activities = []
        for activity_type, package_info in self.activity_catalog.items():
            if package_info.package_name == package_name:
                activities.append(activity_type)
        return sorted(activities)
    
    def get_all_packages(self) -> List[str]:
        """Get all unique package names that provide activities."""
        packages = set()
        for package_info in self.activity_catalog.values():
            packages.add(package_info.package_name)
        
        # Add packages from dependencies that might have custom activities
        for dep in self.dependencies:
            if dep.classification in [DependencyType.CUSTOM_LOCAL, DependencyType.THIRD_PARTY]:
                packages.add(dep.name)
        
        return sorted(packages)