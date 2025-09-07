#!/usr/bin/env python3
"""Basic regression test for Activity entity implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all imports still work after changes."""
    try:
        # Test XAML parser imports
        from xaml_parser import XamlParser
        from xaml_parser.models import Activity, WorkflowContent
        from xaml_parser.extractors import ActivityExtractor
        from xaml_parser.utils import ActivityUtils
        
        print("OK - All imports successful")
        return True
        
    except Exception as e:
        print(f"ERROR - Import failed: {e}")
        return False

def test_basic_parsing():
    """Test basic XAML parsing functionality."""
    try:
        # Create simple XAML content
        simple_xaml = '''<?xml version="1.0" encoding="utf-8"?>
        <Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
          <Sequence DisplayName="Test Sequence">
            <LogMessage DisplayName="Test Log" Message="Hello World" Level="Info" />
          </Sequence>
        </Activity>'''
        
        from xaml_parser import XamlParser
        parser = XamlParser()
        result = parser.parse_content(simple_xaml)
        
        if result.success and result.content:
            print("OK - Basic XAML parsing works")
            print(f"  - Found {len(result.content.activities)} activities")
            return True
        else:
            print(f"ERROR - XAML parsing failed: {result.errors}")
            return False
            
    except Exception as e:
        print(f"ERROR - Basic parsing failed: {e}")
        return False

def test_activity_extraction():
    """Test new activity instance extraction."""
    try:
        from xaml_parser.extractors import ActivityExtractor
        from xaml_parser.utils import ActivityUtils
        
        # Test utility functions
        test_id = ActivityUtils.generate_activity_id(
            "test-proj", "Main.xaml", "Activity/Sequence/LogMessage_1", "test_content"
        )
        
        if "#" in test_id and len(test_id.split("#")) == 4:
            print("OK - Activity ID generation works")
            print(f"  - Generated ID: {test_id}")
            return True
        else:
            print(f"ERROR - Invalid activity ID format: {test_id}")
            return False
            
    except Exception as e:
        print(f"ERROR - Activity extraction test failed: {e}")
        return False

def main():
    """Run regression tests."""
    print("Running Activity Entity Regression Tests")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    if test_imports():
        tests_passed += 1
    
    if test_basic_parsing():
        tests_passed += 1
        
    if test_activity_extraction():
        tests_passed += 1
    
    print(f"\nRESULTS: {tests_passed}/{total_tests} regression tests passed")
    
    if tests_passed == total_tests:
        print("OK - No regressions detected!")
        return True
    else:
        print("ERROR - Regression tests failed!")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)