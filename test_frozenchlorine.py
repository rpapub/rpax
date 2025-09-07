#!/usr/bin/env python3
"""Test Activity instances extraction against FrozenChlorine corpus project.

This script validates the Phase 1 implementation of Activity entities (ADR-009)
against real UiPath workflows from the FrozenChlorine project.
"""

import sys
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from dataclasses import asdict

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xaml_parser.parser import XamlParser
from xaml_parser.extractors import ActivityExtractor
from xaml_parser.utils import ActivityUtils


def test_clicklistofcharacters_extraction():
    """Test activity extraction from ClickListOfCharacters.xaml (the main test case from implementation plan)."""
    print("=== Testing ClickListOfCharacters.xaml ===")
    
    # Path to FrozenChlorine test file
    xaml_file = Path("D:/github.com/rpapub/FrozenChlorine/Process/Calculator/ClickListOfCharacters.xaml")
    
    if not xaml_file.exists():
        print(f"ERROR: Test file not found: {xaml_file}")
        return False
    
    print(f"Reading XAML file: {xaml_file}")
    
    try:
        # Parse XAML file using our parser
        parser = XamlParser()
        result = parser.parse_file(xaml_file)
        
        if not result.success:
            print(f"ERROR: Failed to parse XAML file: {result.errors}")
            return False
        
        print("OK - Successfully parsed XAML file")
        print(f"  - Total activities found: {result.content.total_activities}")
        print(f"  - Root annotation: {result.content.root_annotation[:100] if result.content.root_annotation else 'None'}...")
        print(f"  - Expression language: {result.content.expression_language}")
        
        # Extract activity instances using enhanced extractor
        extractor_config = {
            'extract_expressions': True,
            'expression_language': result.content.expression_language
        }
        extractor = ActivityExtractor(extractor_config)
        
        # Get the root element for processing
        root_element = None
        if hasattr(result, 'root'):
            root_element = result.root
        else:
            # Parse again to get ET.Element
            with open(xaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            root_element = ET.fromstring(content)
        
        # Extract activity instances
        activities = extractor.extract_activity_instances(
            root_element,
            result.content.namespaces,
            "Process/Calculator/ClickListOfCharacters", 
            "frozenchlorine-test"
        )
        
        print(f"OK - Extracted {len(activities)} activity instances")
        
        # Validate key activities mentioned in implementation plan
        print("\n--- Validating Key Activities ---")
        
        # Look for NClick activities 
        nclick_activities = [a for a in activities if a.activity_type == 'NClick']
        print(f"OK - Found {len(nclick_activities)} NClick activities")
        
        if nclick_activities:
            nclick = nclick_activities[0]
            print(f"  - NClick activity ID: {nclick.activity_id}")
            print(f"  - Arguments: {nclick.arguments}")
            print(f"  - Properties: {nclick.properties}")
            print(f"  - Selectors: {list(nclick.selectors.keys())}")
            print(f"  - Expressions: {nclick.expressions}")
            
            # Check for expected arguments from implementation plan
            if 'ActivateBefore' in nclick.arguments:
                print(f"  OK - ActivateBefore argument found: {nclick.arguments['ActivateBefore']}")
            if 'ClickType' in nclick.arguments:
                print(f"  OK - ClickType argument found: {nclick.arguments['ClickType']}")
        
        # Look for ForEach activities
        foreach_activities = [a for a in activities if a.activity_type == 'ForEach']
        print(f"OK - Found {len(foreach_activities)} ForEach activities")
        
        if foreach_activities:
            foreach = foreach_activities[0]
            print(f"  - ForEach activity ID: {foreach.activity_id}")
            print(f"  - Arguments: {foreach.arguments}")
            print(f"  - Variables referenced: {foreach.variables_referenced}")
            print(f"  - Expressions: {foreach.expressions}")
            
            # Check for CharacterList reference
            if 'CharacterList' in foreach.variables_referenced:
                print(f"  OK - CharacterList variable reference found")
        
        # Validate activity ID format
        print("\n--- Validating Activity ID Format ---")
        for i, activity in enumerate(activities[:3]):  # Check first 3
            parts = activity.activity_id.split('#')
            if len(parts) == 4:
                print(f"  OK - Activity {i+1} ID format valid: {activity.activity_id}")
                print(f"    - Project: {parts[0]}")
                print(f"    - Workflow: {parts[1]}")  
                print(f"    - Node: {parts[2][:50]}...")
                print(f"    - Hash: {parts[3]}")
            else:
                print(f"  ERROR - Activity {i+1} ID format invalid: {activity.activity_id}")
        
        # Test serialization (for JSON artifacts)
        print("\n--- Testing JSON Serialization ---")
        try:
            artifact = {
                "schemaVersion": "1.0.0",
                "workflowId": "Process/Calculator/ClickListOfCharacters",
                "totalActivities": len(activities),
                "activities": [asdict(activity) for activity in activities]
            }
            
            json_str = json.dumps(artifact, indent=2, ensure_ascii=False)
            print(f"OK - Successfully serialized to JSON ({len(json_str)} characters)")
            
            # Write sample output
            output_file = Path("test_output_clicklistofcharacters.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"OK - Sample output written to: {output_file}")
            
        except Exception as e:
            print(f"ERROR - JSON serialization failed: {e}")
            return False
        
        print(f"\nOK - All tests passed for ClickListOfCharacters.xaml!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_standard_calculator_extraction():
    """Test activity extraction from StandardCalculator.xaml (main workflow)."""
    print("\n=== Testing StandardCalculator.xaml ===")
    
    xaml_file = Path("D:/github.com/rpapub/FrozenChlorine/StandardCalculator.xaml")
    
    if not xaml_file.exists():
        print(f"ERROR: Test file not found: {xaml_file}")
        return False
    
    try:
        # Parse and extract
        parser = XamlParser()
        result = parser.parse_file(xaml_file)
        
        if not result.success:
            print(f"ERROR: Failed to parse: {result.errors}")
            return False
        
        print(f"OK - Successfully parsed StandardCalculator.xaml")
        
        # Extract activity instances  
        extractor = ActivityExtractor({'extract_expressions': True})
        
        with open(xaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        root_element = ET.fromstring(content)
        
        activities = extractor.extract_activity_instances(
            root_element,
            result.content.namespaces,
            "StandardCalculator",
            "frozenchlorine-test"
        )
        
        print(f"OK - Extracted {len(activities)} activity instances from main workflow")
        
        # Look for InvokeWorkflowFile activities (should call ClickListOfCharacters)
        invoke_activities = [a for a in activities if a.activity_type == 'InvokeWorkflowFile']
        print(f"OK - Found {len(invoke_activities)} InvokeWorkflowFile activities")
        
        for invoke in invoke_activities:
            print(f"  - Workflow invocation: {invoke.arguments.get('WorkflowFileName', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Run all FrozenChlorine corpus tests."""
    print("Testing Activity Entity Implementation (Phase 1)")
    print("=" * 60)
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    if test_clicklistofcharacters_extraction():
        tests_passed += 1
    
    if test_standard_calculator_extraction():
        tests_passed += 1
    
    print(f"\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("OK - All FrozenChlorine corpus tests passed!")
        return True
    else:
        print("ERROR - Some tests failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)