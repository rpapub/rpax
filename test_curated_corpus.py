#!/usr/bin/env python3
"""Test Activity instances extraction against curated test corpus.

This script validates the Activity entity implementation against our
curated test corpus with known expected results.
"""

import sys
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xaml_parser.parser import XamlParser
from xaml_parser.extractors import ActivityExtractor
from xaml_parser.utils import ActivityUtils
from xaml_parser.models import Activity


def test_simple_sequence():
    """Test the simple sequence XAML file."""
    print("=== Testing simple_sequence.xaml ===")
    
    xaml_file = Path(__file__).parent / "src" / "xaml_parser" / "test_data" / "simple_sequence.xaml"
    
    try:
        parser = XamlParser()
        result = parser.parse_file(xaml_file)
        
        if not result.success:
            print(f"ERROR: Failed to parse: {result.errors}")
            return False
        
        print(f"OK - Parsed successfully")
        print(f"  - Total activities: {result.content.total_activities}")
        print(f"  - Expression language: {result.content.expression_language}")
        
        # Extract activity instances
        extractor = ActivityExtractor({'extract_expressions': True})
        
        with open(xaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        root_element = ET.fromstring(content)
        
        activities = extractor.extract_activity_instances(
            root_element,
            result.content.namespaces,
            "simple_sequence",
            "test-corpus"
        )
        
        print(f"OK - Extracted {len(activities)} activity instances")
        
        # Validate expected activity types
        expected_types = {'Sequence', 'Assign', 'LogMessage', 'If'}
        found_types = {activity.activity_type for activity in activities}
        
        print(f"Activity types found: {sorted(found_types)}")
        
        # Check for expected types
        for expected_type in expected_types:
            matching_activities = [a for a in activities if a.activity_type == expected_type]
            if matching_activities:
                print(f"  OK - Found {len(matching_activities)} {expected_type} activities")
            else:
                print(f"  WARN - No {expected_type} activities found")
        
        # Check variables
        variables_referenced = set()
        for activity in activities:
            variables_referenced.update(activity.variables_referenced)
        
        expected_vars = {'testMessage', 'counter'}
        found_vars = variables_referenced & expected_vars
        print(f"Variables referenced: {sorted(variables_referenced)}")
        print(f"Expected variables found: {sorted(found_vars)}")
        
        return len(activities) >= 4  # Should have at least 4 activities
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_automation_sample():
    """Test the UI automation sample XAML file."""
    print("\n=== Testing ui_automation_sample.xaml ===")
    
    xaml_file = Path(__file__).parent / "src" / "xaml_parser" / "test_data" / "ui_automation_sample.xaml"
    
    try:
        parser = XamlParser()
        result = parser.parse_file(xaml_file)
        
        if not result.success:
            print(f"ERROR: Failed to parse: {result.errors}")
            return False
        
        print(f"OK - Parsed successfully")
        
        # Extract activity instances
        extractor = ActivityExtractor({'extract_expressions': True})
        
        with open(xaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        root_element = ET.fromstring(content)
        
        activities = extractor.extract_activity_instances(
            root_element,
            result.content.namespaces,
            "ui_automation_sample",
            "test-corpus"
        )
        
        print(f"OK - Extracted {len(activities)} activity instances")
        
        # Check for UI automation specific activities
        ui_activities = [a for a in activities if a.activity_type in ['Click', 'TypeInto', 'ElementExists']]
        print(f"UI automation activities: {len(ui_activities)}")
        
        for ui_activity in ui_activities:
            print(f"  - {ui_activity.activity_type}: {ui_activity.display_name}")
            if ui_activity.selectors:
                print(f"    Selectors: {list(ui_activity.selectors.keys())}")
        
        # Check for selectors
        activities_with_selectors = [a for a in activities if a.selectors]
        print(f"Activities with selectors: {len(activities_with_selectors)}")
        
        return len(ui_activities) >= 3  # Should have Click, TypeInto, ElementExists
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_complex_workflow():
    """Test the complex workflow XAML file."""
    print("\n=== Testing complex_workflow.xaml ===")
    
    xaml_file = Path(__file__).parent / "src" / "xaml_parser" / "test_data" / "complex_workflow.xaml"
    
    try:
        parser = XamlParser()
        result = parser.parse_file(xaml_file)
        
        if not result.success:
            print(f"ERROR: Failed to parse: {result.errors}")
            return False
        
        print(f"OK - Parsed successfully")
        
        # Extract activity instances
        extractor = ActivityExtractor({'extract_expressions': True})
        
        with open(xaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        root_element = ET.fromstring(content)
        
        activities = extractor.extract_activity_instances(
            root_element,
            result.content.namespaces,
            "complex_workflow",
            "test-corpus"
        )
        
        print(f"OK - Extracted {len(activities)} activity instances")
        
        # Check for complex control structures
        control_structures = ['TryCatch', 'ForEach', 'Switch']
        for control_type in control_structures:
            matching = [a for a in activities if a.activity_type == control_type]
            print(f"  - {control_type}: {len(matching)} instances")
        
        # Check activity type distribution
        activity_types = {}
        for activity in activities:
            activity_type = activity.activity_type
            activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
        
        print(f"Activity type distribution: {dict(sorted(activity_types.items()))}")
        
        return len(activities) >= 10  # Should have many nested activities
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_invoke_workflows_sample():
    """Test the workflow invocation sample XAML file."""
    print("\n=== Testing invoke_workflows_sample.xaml ===")
    
    xaml_file = Path(__file__).parent / "src" / "xaml_parser" / "test_data" / "invoke_workflows_sample.xaml"
    
    try:
        parser = XamlParser()
        result = parser.parse_file(xaml_file)
        
        if not result.success:
            print(f"ERROR: Failed to parse: {result.errors}")
            return False
        
        print(f"OK - Parsed successfully")
        
        # Extract activity instances
        extractor = ActivityExtractor({'extract_expressions': True})
        
        with open(xaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        root_element = ET.fromstring(content)
        
        activities = extractor.extract_activity_instances(
            root_element,
            result.content.namespaces,
            "invoke_workflows_sample",
            "test-corpus"
        )
        
        print(f"OK - Extracted {len(activities)} activity instances")
        
        # Check for InvokeWorkflowFile activities
        invoke_activities = [a for a in activities if a.activity_type == 'InvokeWorkflowFile']
        print(f"Workflow invocations: {len(invoke_activities)}")
        
        for invoke in invoke_activities:
            workflow_file = invoke.arguments.get('WorkflowFileName', 'Unknown')
            print(f"  - Invokes: {workflow_file}")
        
        return len(invoke_activities) >= 3  # Should have 3 InvokeWorkflowFile activities
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Run all curated corpus tests."""
    print("Testing Activity Entity Implementation")
    print("Against Curated Test Corpus")
    print("=" * 50)
    
    tests = [
        test_simple_sequence,
        test_ui_automation_sample,
        test_complex_workflow,
        test_invoke_workflows_sample,
    ]
    
    tests_passed = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                tests_passed += 1
            else:
                print("  FAILED")
        except Exception as e:
            print(f"  EXCEPTION: {e}")
    
    print(f"\n" + "=" * 50)
    print(f"RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("OK - All curated corpus tests passed!")
        return True
    else:
        print("ERROR - Some tests failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)