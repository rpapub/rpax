"""Namespace and package analysis for UiPath XAML workflows."""

import re
from pathlib import Path
from typing import Dict, List, Set
from xml.etree.ElementTree import Element, parse as xml_parse

from defusedxml.ElementTree import parse as defused_parse


class NamespaceAnalyzer:
    """Analyzes XAML namespaces to extract package usage information."""
    
    # Known UiPath package namespace patterns
    UIPATH_NAMESPACE_PATTERNS = {
        r"http://schemas\.uipath\.com/workflow/activities": "UiPath.System.Activities",
        r"clr-namespace:UiPath\.([^;]+)(?:;assembly=([^;]+))?": r"UiPath.\1",
        r"clr-namespace:.*\.Activities(?:\.([^;]+))?;assembly=UiPath\.([^;]+)\.Activities": r"UiPath.\2.Activities",
        r"clr-namespace:.*Activities;assembly=([^;]+)": r"\1",
    }
    
    # Standard .NET/XAML namespaces that should be ignored
    SYSTEM_NAMESPACES = {
        "http://schemas.microsoft.com/winfx/2006/xaml",
        "http://schemas.microsoft.com/netfx/2009/xaml/activities", 
        "http://schemas.microsoft.com/winfx/2006/xaml/presentation",
        "http://schemas.openxmlformats.org/markup-compatibility/2006",
        "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation",
        "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation",
        "clr-namespace:System",
        "clr-namespace:System.Activities",
        "clr-namespace:System.Collections",
        "clr-namespace:System.Collections.Generic",
        "clr-namespace:Microsoft.VisualBasic",
    }

    def __init__(self):
        """Initialize namespace analyzer."""
        pass

    def extract_namespaces_from_xaml(self, xaml_path: Path) -> Dict[str, str]:
        """Extract all xmlns namespace declarations from XAML file.
        
        Args:
            xaml_path: Path to XAML workflow file
            
        Returns:
            Dict mapping prefixes to namespace URIs
        """
        # Use text parsing as primary method since XML parsers consume namespace declarations
        try:
            return self._extract_namespaces_text_fallback(xaml_path)
        except Exception:
            # If text parsing fails, try XML parsing as fallback
            namespaces = {}
            
            try:
                # Use defused XML for security
                tree = defused_parse(xaml_path)
                root = tree.getroot()
                
                # Extract namespace declarations from root element
                for attr_name, attr_value in root.attrib.items():
                    if attr_name == "xmlns":
                        # Default namespace
                        namespaces[""] = attr_value
                    elif attr_name.startswith("xmlns:"):
                        # Prefixed namespace
                        prefix = attr_name[6:]  # Remove "xmlns:" prefix
                        namespaces[prefix] = attr_value
                        
            except Exception:
                pass  # Return empty dict if all parsing methods fail
                
            return namespaces

    def _extract_namespaces_text_fallback(self, xaml_path: Path) -> Dict[str, str]:
        """Fallback namespace extraction using text parsing.
        
        Args:
            xaml_path: Path to XAML workflow file
            
        Returns:
            Dict mapping prefixes to namespace URIs
        """
        namespaces = {}
        
        try:
            content = xaml_path.read_text(encoding="utf-8")
            
            # Extract xmlns declarations using regex
            xmlns_pattern = r'xmlns(?::([^=]+))?="([^"]+)"'
            matches = re.findall(xmlns_pattern, content)
            
            for prefix, namespace_uri in matches:
                key = prefix if prefix else ""
                namespaces[key] = namespace_uri
                
        except Exception:
            pass  # Return empty dict on any error
            
        return namespaces

    def extract_packages_from_namespaces(self, namespaces: Dict[str, str]) -> List[str]:
        """Extract UiPath package names from namespace URIs.
        
        Args:
            namespaces: Dict mapping prefixes to namespace URIs
            
        Returns:
            List of UiPath package names
        """
        packages = set()
        
        for prefix, namespace_uri in namespaces.items():
            # Skip system namespaces
            if self._is_system_namespace(namespace_uri):
                continue
                
            # Try to extract package name using patterns
            package_name = self._extract_package_name(namespace_uri)
            if package_name:
                packages.add(package_name)
                
        return sorted(packages)

    def _is_system_namespace(self, namespace_uri: str) -> bool:
        """Check if namespace is a system/framework namespace.
        
        Args:
            namespace_uri: Namespace URI to check
            
        Returns:
            True if this is a system namespace
        """
        for system_ns in self.SYSTEM_NAMESPACES:
            if namespace_uri == system_ns or namespace_uri.startswith(system_ns):
                return True
        return False

    def _extract_package_name(self, namespace_uri: str) -> str | None:
        """Extract package name from namespace URI.
        
        Args:
            namespace_uri: Namespace URI to analyze
            
        Returns:
            Package name or None if not extractable
        """
        # Try each pattern
        for pattern, replacement in self.UIPATH_NAMESPACE_PATTERNS.items():
            match = re.search(pattern, namespace_uri)
            if match:
                if isinstance(replacement, str) and r"\1" in replacement:
                    # Use regex substitution
                    return re.sub(pattern, replacement, namespace_uri)
                else:
                    # Direct replacement
                    return replacement
                    
        # Check for UiPath assembly references in clr-namespace
        if "clr-namespace:" in namespace_uri and "UiPath" in namespace_uri:
            # Extract assembly name
            assembly_match = re.search(r"assembly=([^;]+)", namespace_uri)
            if assembly_match:
                assembly_name = assembly_match.group(1)
                # Clean up common assembly names
                if assembly_name.startswith("UiPath."):
                    return assembly_name
                elif "." in assembly_name:
                    return assembly_name
                    
        return None

    def analyze_workflow_packages(self, xaml_path: Path) -> Dict[str, any]:
        """Analyze workflow for complete package usage information.
        
        Args:
            xaml_path: Path to XAML workflow file
            
        Returns:
            Dict with namespaces and extracted packages
        """
        namespaces = self.extract_namespaces_from_xaml(xaml_path)
        packages = self.extract_packages_from_namespaces(namespaces)
        
        return {
            "namespaces": namespaces,
            "packages_used": packages,
            "total_namespaces": len(namespaces),
            "total_packages": len(packages)
        }