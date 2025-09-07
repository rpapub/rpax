"""Tests for namespace and package analysis functionality."""

import tempfile
from pathlib import Path
import pytest

from rpax.parser.namespace_analyzer import NamespaceAnalyzer


class TestNamespaceAnalyzer:
    """Test namespace and package analysis functionality."""

    def test_extract_namespaces_from_xaml(self):
        """Test basic namespace extraction from XAML."""
        analyzer = NamespaceAnalyzer()
        
        # Create a simple XAML with namespaces
        xaml_content = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010" x:Class="TestWorkflow" 
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" 
  xmlns:av="http://schemas.microsoft.com/winfx/2006/xaml/presentation" 
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" 
  xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation" 
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation" 
  xmlns:ui="http://schemas.uipath.com/workflow/activities" 
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
</Activity>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xaml', delete=False, encoding='utf-8') as f:
            f.write(xaml_content)
            f.flush()
            xaml_path = Path(f.name)

        try:
            namespaces = analyzer.extract_namespaces_from_xaml(xaml_path)
            
            # Check that we extracted expected namespaces
            assert "" in namespaces  # Default namespace
            assert "ui" in namespaces
            assert "x" in namespaces
            assert "sap" in namespaces
            
            assert namespaces["ui"] == "http://schemas.uipath.com/workflow/activities"
            assert namespaces["x"] == "http://schemas.microsoft.com/winfx/2006/xaml"
            
        finally:
            xaml_path.unlink()

    def test_extract_packages_from_namespaces(self):
        """Test package extraction from namespace URIs."""
        analyzer = NamespaceAnalyzer()
        
        namespaces = {
            "": "http://schemas.microsoft.com/netfx/2009/xaml/activities",
            "ui": "http://schemas.uipath.com/workflow/activities", 
            "x": "http://schemas.microsoft.com/winfx/2006/xaml",
            "excel": "clr-namespace:UiPath.Excel.Activities;assembly=UiPath.Excel.Activities",
            "mail": "clr-namespace:UiPath.Mail.Activities;assembly=UiPath.Mail.Activities"
        }
        
        packages = analyzer.extract_packages_from_namespaces(namespaces)
        
        # Should extract UiPath packages but not system namespaces
        assert "UiPath.System.Activities" in packages
        assert "UiPath.Excel.Activities" in packages  
        assert "UiPath.Mail.Activities" in packages
        
        # Should not include system namespaces
        assert len([p for p in packages if "Microsoft" in p]) == 0

    def test_analyze_workflow_packages(self):
        """Test complete workflow package analysis."""
        analyzer = NamespaceAnalyzer()
        
        # Create XAML with UiPath namespaces
        xaml_content = '''<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010" x:Class="TestWorkflow"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:excel="clr-namespace:UiPath.Excel.Activities;assembly=UiPath.Excel.Activities"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence>
    <ui:LogMessage Message="Test" />
    <excel:ReadCell />
  </Sequence>
</Activity>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xaml', delete=False, encoding='utf-8') as f:
            f.write(xaml_content)
            f.flush()
            xaml_path = Path(f.name)

        try:
            result = analyzer.analyze_workflow_packages(xaml_path)
            
            assert "namespaces" in result
            assert "packages_used" in result
            assert "total_namespaces" in result
            assert "total_packages" in result
            
            # Should have extracted namespaces
            assert result["total_namespaces"] > 0
            assert "ui" in result["namespaces"]
            assert "excel" in result["namespaces"]
            
            # Should have identified packages
            packages = result["packages_used"]
            assert "UiPath.System.Activities" in packages
            assert "UiPath.Excel.Activities" in packages
            
        finally:
            xaml_path.unlink()

    def test_is_system_namespace(self):
        """Test system namespace detection."""
        analyzer = NamespaceAnalyzer()
        
        # System namespaces should be detected
        assert analyzer._is_system_namespace("http://schemas.microsoft.com/winfx/2006/xaml")
        assert analyzer._is_system_namespace("clr-namespace:System.Activities")
        assert analyzer._is_system_namespace("clr-namespace:System")
        
        # UiPath namespaces should not be system namespaces
        assert not analyzer._is_system_namespace("http://schemas.uipath.com/workflow/activities")
        assert not analyzer._is_system_namespace("clr-namespace:UiPath.Excel.Activities;assembly=UiPath.Excel.Activities")

    def test_extract_package_name(self):
        """Test individual package name extraction."""
        analyzer = NamespaceAnalyzer()
        
        # UiPath system activities
        assert analyzer._extract_package_name("http://schemas.uipath.com/workflow/activities") == "UiPath.System.Activities"
        
        # UiPath package with assembly
        assert analyzer._extract_package_name("clr-namespace:UiPath.Excel.Activities;assembly=UiPath.Excel.Activities") == "UiPath.Excel.Activities"
        
        # Third party package
        assert analyzer._extract_package_name("clr-namespace:SomeThirdParty.Activities;assembly=SomeThirdParty.Package") == "SomeThirdParty.Package"
        
        # System namespace should return None
        assert analyzer._extract_package_name("http://schemas.microsoft.com/winfx/2006/xaml") is None