#!/usr/bin/env python3
"""Test Activity instances extraction against PurposefulPromethium corpus project.

This script validates the Phase 2 implementation of Activity entities (ADR-009)
against a complex UiPath project with multiple workflows, framework components,
and test cases from the PurposefulPromethium project.
"""

import sys
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict
from typing import List, Dict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xaml_parser.parser import XamlParser
from xaml_parser.extractors import ActivityExtractor
from xaml_parser.utils import ActivityUtils
from xaml_parser.models import Activity


def test_main_workflow_extraction():
    """Test activity extraction from Main.xaml (main entry point)."""
    print("=== Testing PurposefulPromethium Main.xaml ===")
    
    # Path to PurposefulPromethium main workflow
    xaml_file = Path("D:/github.com/rpapub/PurposefulPromethium/Main.xaml")
    
    if not xaml_file.exists():
        print(f"ERROR: Test file not found: {xaml_file}")
        return False
    
    print(f"Reading main workflow: {xaml_file}")
    
    try:
        # Parse XAML file using our parser
        parser = XamlParser()
        result = parser.parse_file(xaml_file)
        
        if not result.success:
            print(f"ERROR: Failed to parse XAML file: {result.errors}")
            return False
        
        print("OK - Successfully parsed Main.xaml")
        print(f"  - Total activities found: {result.content.total_activities}")
        print(f"  - Expression language: {result.content.expression_language}")
        print(f"  - Namespaces: {len(result.content.namespaces)}")
        
        # Extract activity instances
        extractor_config = {
            'extract_expressions': True,
            'expression_language': result.content.expression_language
        }
        extractor = ActivityExtractor(extractor_config)
        
        # Parse content to get root element
        with open(xaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        root_element = ET.fromstring(content)
        
        # Extract activity instances
        activities = extractor.extract_activity_instances(
            root_element,
            result.content.namespaces,
            "Main", 
            "PurposefulPromethium"
        )
        
        print(f"OK - Extracted {len(activities)} activity instances from Main.xaml")
        
        # Validate specific activity types expected in email automation workflow
        print("\n--- Validating Key Activity Types ---")
        
        activity_types = {}
        for activity in activities:
            activity_type = activity.activity_type
            activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
        
        print(f"Activity type distribution:")
        for act_type, count in sorted(activity_types.items()):
            print(f"  - {act_type}: {count}")
        
        # Look for common email automation activities
        expected_types = ['Sequence', 'Assign', 'LogMessage', 'InvokeWorkflowFile']
        for expected_type in expected_types:
            if expected_type in activity_types:
                print(f"OK - Found {activity_types[expected_type]} {expected_type} activities")
            else:
                print(f"INFO - No {expected_type} activities found")
        
        # Check for InvokeWorkflowFile activities (framework calls)
        invoke_activities = [a for a in activities if a.activity_type == 'InvokeWorkflowFile']
        if invoke_activities:
            print(f"OK - Found {len(invoke_activities)} workflow invocations:")
            for invoke in invoke_activities[:3]:  # Show first 3
                workflow_file = invoke.arguments.get('WorkflowFileName', 'Unknown')
                print(f"  - Invokes: {workflow_file}")
        
        # Test serialization for artifacts
        print("\n--- Testing JSON Serialization ---")
        try:
            artifact = {
                "schemaVersion": "1.0.0",
                "workflowId": "Main",
                "projectId": "PurposefulPromethium",
                "totalActivities": len(activities),
                "activityTypes": activity_types,
                "activities": [asdict(activity) for activity in activities[:5]]  # Limit to first 5
            }
            
            json_str = json.dumps(artifact, indent=2, ensure_ascii=False)
            print(f"OK - Successfully serialized to JSON ({len(json_str)} characters)")
            
            # Write sample output
            output_file = Path("test_output_purposeful_promethium_main.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"OK - Sample output written to: {output_file}")
            
        except Exception as e:
            print(f"ERROR - JSON serialization failed: {e}")
            return False
        
        print(f"\nOK - Main.xaml test passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_framework_workflow_extraction():
    """Test activity extraction from Framework workflows."""
    print("\n=== Testing Framework Workflows ===")
    
    framework_dir = Path("D:/github.com/rpapub/PurposefulPromethium/Framework")
    
    if not framework_dir.exists():
        print(f"ERROR: Framework directory not found: {framework_dir}")
        return False
    
    # Find XAML files in Framework directory
    xaml_files = list(framework_dir.rglob("*.xaml"))
    
    if not xaml_files:
        print("INFO - No XAML files found in Framework directory")
        return True
    
    print(f"Found {len(xaml_files)} framework workflows:")
    
    total_activities = 0
    processed_workflows = 0
    
    for xaml_file in xaml_files[:3]:  # Test first 3 framework workflows
        print(f"\nTesting framework workflow: {xaml_file.name}")
        
        try:
            parser = XamlParser()
            result = parser.parse_file(xaml_file)
            
            if not result.success:
                print(f"  SKIP - Failed to parse: {result.errors}")
                continue
            
            # Extract activity instances
            extractor = ActivityExtractor({'extract_expressions': True})
            
            with open(xaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            root_element = ET.fromstring(content)
            
            workflow_id = str(xaml_file.relative_to(framework_dir.parent)).replace("\\", "/").replace(".xaml", "")
            
            activities = extractor.extract_activity_instances(
                root_element,
                result.content.namespaces,
                workflow_id,
                "PurposefulPromethium"
            )
            
            print(f"  OK - Extracted {len(activities)} activities")
            total_activities += len(activities)
            processed_workflows += 1
            
            # Show activity type distribution for this workflow
            if activities:
                activity_types = {}
                for activity in activities:
                    activity_type = activity.activity_type
                    activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
                
                # Show top 3 activity types
                top_types = sorted(activity_types.items(), key=lambda x: x[1], reverse=True)[:3]
                type_summary = ", ".join([f"{t}:{c}" for t, c in top_types])
                print(f"    Top types: {type_summary}")
        
        except Exception as e:
            print(f"  ERROR - Failed to process {xaml_file.name}: {e}")
            continue
    
    print(f"\nFramework workflows summary:")
    print(f"  - Processed: {processed_workflows}/{min(len(xaml_files), 3)} workflows")
    print(f"  - Total activities: {total_activities}")
    
    return processed_workflows > 0


def test_process_workflow_extraction():
    """Test activity extraction from Process workflows."""
    print("\n=== Testing Process Workflows ===")
    
    process_dir = Path("D:/github.com/rpapub/PurposefulPromethium/Process")
    
    if not process_dir.exists():
        print(f"ERROR: Process directory not found: {process_dir}")
        return False
    
    # Find XAML files in Process directory
    xaml_files = list(process_dir.rglob("*.xaml"))
    
    if not xaml_files:
        print("INFO - No XAML files found in Process directory")
        return True
    
    print(f"Found {len(xaml_files)} process workflows")
    
    total_activities = 0
    processed_workflows = 0
    
    for xaml_file in xaml_files[:3]:  # Test first 3 process workflows
        print(f"\nTesting process workflow: {xaml_file.name}")
        
        try:
            parser = XamlParser()
            result = parser.parse_file(xaml_file)
            
            if not result.success:
                print(f"  SKIP - Failed to parse: {result.errors}")
                continue
            
            # Extract activity instances
            extractor = ActivityExtractor({'extract_expressions': True})
            
            with open(xaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            root_element = ET.fromstring(content)
            
            workflow_id = str(xaml_file.relative_to(process_dir.parent)).replace("\\", "/").replace(".xaml", "")
            
            activities = extractor.extract_activity_instances(
                root_element,
                result.content.namespaces,
                workflow_id,
                "PurposefulPromethium"
            )
            
            print(f"  OK - Extracted {len(activities)} activities")
            total_activities += len(activities)
            processed_workflows += 1
            
            # Look for email automation specific activities
            email_activities = [a for a in activities if any(keyword in a.activity_type.lower() 
                               for keyword in ['mail', 'imap', 'smtp', 'email', 'message'])]
            
            if email_activities:
                print(f"    Found {len(email_activities)} email-related activities")
                for email_act in email_activities[:2]:  # Show first 2
                    print(f"      - {email_act.activity_type}")
        
        except Exception as e:
            print(f"  ERROR - Failed to process {xaml_file.name}: {e}")
            continue
    
    print(f"\nProcess workflows summary:")
    print(f"  - Processed: {processed_workflows}/{min(len(xaml_files), 3)} workflows")
    print(f"  - Total activities: {total_activities}")
    
    return processed_workflows > 0


def test_activity_id_uniqueness():
    """Test that activity IDs are unique across the project."""
    print("\n=== Testing Activity ID Uniqueness ===")
    
    project_root = Path("D:/github.com/rpapub/PurposefulPromethium")
    
    # Find all XAML files in project
    xaml_files = list(project_root.rglob("*.xaml"))[:5]  # Test first 5 files
    
    all_activity_ids = set()
    total_activities = 0
    
    for xaml_file in xaml_files:
        try:
            parser = XamlParser()
            result = parser.parse_file(xaml_file)
            
            if not result.success:
                continue
            
            extractor = ActivityExtractor({'extract_expressions': True})
            
            with open(xaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            root_element = ET.fromstring(content)
            
            workflow_id = str(xaml_file.relative_to(project_root)).replace("\\", "/").replace(".xaml", "")
            
            activities = extractor.extract_activity_instances(
                root_element,
                result.content.namespaces,
                workflow_id,
                "PurposefulPromethium"
            )
            
            # Check for ID collisions
            file_ids = set()
            for activity in activities:
                if activity.activity_id in all_activity_ids:
                    print(f"ERROR - Duplicate activity ID found: {activity.activity_id}")
                    return False
                
                all_activity_ids.add(activity.activity_id)
                file_ids.add(activity.activity_id)
            
            total_activities += len(activities)
            print(f"  {xaml_file.name}: {len(activities)} activities, {len(file_ids)} unique IDs")
        
        except Exception as e:
            print(f"  SKIP - {xaml_file.name}: {e}")
            continue
    
    print(f"OK - All {total_activities} activity IDs are unique across {len(xaml_files)} workflows")
    return True


def main():
    """Run all PurposefulPromethium corpus tests."""
    print("Testing Activity Entity Implementation - Phase 2")
    print("Against PurposefulPromethium Corpus Project")
    print("=" * 60)
    
    # Run tests
    tests_passed = 0
    total_tests = 4
    
    if test_main_workflow_extraction():
        tests_passed += 1
    
    if test_framework_workflow_extraction():
        tests_passed += 1
    
    if test_process_workflow_extraction():
        tests_passed += 1
    
    if test_activity_id_uniqueness():
        tests_passed += 1
    
    print(f"\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("OK - All PurposefulPromethium corpus tests passed!")
        return True
    else:
        print("ERROR - Some tests failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)