#!/usr/bin/env python3
"""Golden freeze test system for Activity entity implementation.

This script compares actual activity extraction results against golden
freeze results to detect regressions and validate implementation changes.
"""

import sys
import json
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from dataclasses import asdict
from typing import Dict, List, Any, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xaml_parser.parser import XamlParser
from xaml_parser.extractors import ActivityExtractor
from xaml_parser.utils import ActivityUtils
from xaml_parser.models import Activity


class GoldenFreezeValidator:
    """Validates activity extraction results against golden freeze expectations."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_data_dir = Path(__file__).parent / "src" / "xaml_parser" / "test_data"
    
    def run_all_tests(self) -> Tuple[int, int]:
        """Run all golden freeze tests and return (passed, total) counts."""
        test_files = [
            "simple_sequence.xaml",
            "ui_automation_sample.xaml", 
            "complex_workflow.xaml",
            "invoke_workflows_sample.xaml"
        ]
        
        passed = 0
        total = len(test_files)
        
        print("Running Golden Freeze Tests")
        print("=" * 50)
        
        for test_file in test_files:
            print(f"\n=== Testing {test_file} ===")
            
            if self.validate_test_case(test_file):
                print("PASS")
                passed += 1
            else:
                print("FAIL")
        
        return passed, total
    
    def validate_test_case(self, xaml_filename: str) -> bool:
        """Validate a single test case against its golden results."""
        xaml_file = self.test_data_dir / xaml_filename
        golden_file = self.test_data_dir / (xaml_filename.replace('.xaml', '_golden.json'))
        
        if not xaml_file.exists():
            print(f"ERROR: XAML file not found: {xaml_file}")
            return False
        
        if not golden_file.exists():
            print(f"ERROR: Golden file not found: {golden_file}")
            return False
        
        try:
            # Load golden expectations
            with open(golden_file, 'r', encoding='utf-8') as f:
                golden_data = json.load(f)
            
            # Extract actual results
            actual_results = self.extract_test_results(xaml_file)
            
            if not actual_results:
                print("ERROR: Failed to extract actual results")
                return False
            
            # Compare results
            return self.compare_results(actual_results, golden_data)
            
        except Exception as e:
            print(f"ERROR: Exception during validation: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
    
    def extract_test_results(self, xaml_file: Path) -> Dict[str, Any]:
        """Extract actual results from XAML file for comparison."""
        try:
            # Parse XAML file
            parser = XamlParser()
            result = parser.parse_file(xaml_file)
            
            if not result.success:
                print(f"ERROR: Failed to parse XAML: {result.errors}")
                return {}
            
            # Extract activity instances
            extractor = ActivityExtractor({'extract_expressions': True})
            
            with open(xaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            root_element = ET.fromstring(content)
            
            test_name = xaml_file.stem
            activities = extractor.extract_activity_instances(
                root_element,
                result.content.namespaces,
                test_name,
                "test-corpus"
            )
            
            # Build comparable results structure
            actual_results = {
                "totalActivities": len(activities),
                "activityTypes": self._get_activity_type_counts(activities),
                "variablesReferenced": self._get_all_variables_referenced(activities),
                "expressionLanguage": result.content.expression_language,
                "namespaceCount": len(result.content.namespaces),
                "keyActivities": self._extract_key_activities(activities),
                "hasAnnotation": result.content.root_annotation is not None,
                "activitiesWithSelectors": len([a for a in activities if a.selectors]),
            }
            
            # Add test-specific metrics
            if "ui_automation" in test_name:
                ui_activities = [a for a in activities if a.activity_type in ['Click', 'TypeInto', 'ElementExists']]
                actual_results["uiAutomationActivities"] = len(ui_activities)
                actual_results["hasWebSelectors"] = any("webctrl" in str(a.selectors) for a in activities if a.selectors)
            
            if "complex_workflow" in test_name:
                control_structures = ['TryCatch', 'ForEach', 'Switch']
                actual_results["controlStructures"] = {
                    cs: len([a for a in activities if a.activity_type == cs]) 
                    for cs in control_structures
                }
                actual_results["hasExceptionHandling"] = any(a.activity_type == 'TryCatch' for a in activities)
            
            if "invoke_workflows" in test_name:
                invoke_activities = [a for a in activities if a.activity_type == 'InvokeWorkflowFile']
                actual_results["workflowInvocations"] = len(invoke_activities)
                actual_results["invokedWorkflows"] = [
                    a.arguments.get('WorkflowFileName', '') for a in invoke_activities
                ]
                actual_results["frameworkPattern"] = any(
                    "Framework" in wf for wf in actual_results["invokedWorkflows"]
                )
            
            return actual_results
            
        except Exception as e:
            print(f"ERROR: Failed to extract results: {e}")
            return {}
    
    def compare_results(self, actual: Dict[str, Any], golden_data: Dict[str, Any]) -> bool:
        """Compare actual results against golden expectations."""
        expected = golden_data["expectedResults"]
        tolerances = golden_data.get("tolerances", {})
        
        all_passed = True
        
        # Check total activities
        if not self._check_total_activities(actual, expected, tolerances):
            all_passed = False
        
        # Check activity types
        if not self._check_activity_types(actual, expected):
            all_passed = False
        
        # Check variables
        if not self._check_variables(actual, expected):
            all_passed = False
        
        # Check expression language
        if actual.get("expressionLanguage") != expected.get("expressionLanguage"):
            print(f"  MISMATCH: Expression language - expected {expected.get('expressionLanguage')}, got {actual.get('expressionLanguage')}")
            all_passed = False
        
        # Check key activities
        if not self._check_key_activities(actual, expected):
            all_passed = False
        
        # Check test-specific requirements
        if not self._check_test_specific(actual, expected, tolerances):
            all_passed = False
        
        return all_passed
    
    def _check_total_activities(self, actual: Dict, expected: Dict, tolerances: Dict) -> bool:
        """Check total activity count within tolerance."""
        actual_count = actual.get("totalActivities", 0)
        expected_count = expected.get("totalActivities", 0)
        
        if "totalActivitiesRange" in tolerances:
            min_count, max_count = tolerances["totalActivitiesRange"]
            if not (min_count <= actual_count <= max_count):
                print(f"  MISMATCH: Total activities {actual_count} outside range [{min_count}, {max_count}]")
                return False
        elif actual_count != expected_count:
            print(f"  MISMATCH: Total activities - expected {expected_count}, got {actual_count}")
            return False
        
        if self.verbose:
            print(f"  OK: Total activities: {actual_count}")
        return True
    
    def _check_activity_types(self, actual: Dict, expected: Dict) -> bool:
        """Check activity type distribution."""
        actual_types = actual.get("activityTypes", {})
        expected_types = expected.get("activityTypes", {})
        
        all_passed = True
        
        for activity_type, expected_count in expected_types.items():
            actual_count = actual_types.get(activity_type, 0)
            if actual_count != expected_count:
                print(f"  MISMATCH: {activity_type} activities - expected {expected_count}, got {actual_count}")
                all_passed = False
            elif self.verbose:
                print(f"  OK: {activity_type}: {actual_count}")
        
        return all_passed
    
    def _check_variables(self, actual: Dict, expected: Dict) -> bool:
        """Check variable references."""
        actual_vars = set(actual.get("variablesReferenced", []))
        expected_vars = set(expected.get("variablesReferenced", []))
        
        if actual_vars != expected_vars:
            missing = expected_vars - actual_vars
            extra = actual_vars - expected_vars
            
            if missing:
                print(f"  MISMATCH: Missing variables: {sorted(missing)}")
            if extra:
                print(f"  INFO: Extra variables: {sorted(extra)}")
            
            # Only fail if expected variables are missing
            return len(missing) == 0
        
        if self.verbose:
            print(f"  OK: Variables: {sorted(actual_vars)}")
        return True
    
    def _check_key_activities(self, actual: Dict, expected: Dict) -> bool:
        """Check key activity specifications."""
        actual_activities = actual.get("keyActivities", [])
        expected_activities = expected.get("keyActivities", [])
        
        # Create lookup by activity type and display name
        actual_lookup = {
            (act["activityType"], act.get("displayName", "")): act 
            for act in actual_activities
        }
        
        all_passed = True
        
        for expected_activity in expected_activities:
            activity_type = expected_activity["activityType"]
            display_name = expected_activity.get("displayName", "")
            key = (activity_type, display_name)
            
            if key not in actual_lookup:
                print(f"  MISMATCH: Key activity not found - {activity_type}: {display_name}")
                all_passed = False
                continue
            
            # Check specific properties
            actual_activity = actual_lookup[key]
            
            for prop, expected_value in expected_activity.items():
                if prop in ["activityType", "displayName"]:
                    continue
                
                actual_value = actual_activity.get(prop)
                if actual_value != expected_value:
                    print(f"  MISMATCH: {activity_type}.{prop} - expected {expected_value}, got {actual_value}")
                    all_passed = False
        
        return all_passed
    
    def _check_test_specific(self, actual: Dict, expected: Dict, tolerances: Dict) -> bool:
        """Check test-specific requirements."""
        all_passed = True
        
        # UI automation specific checks
        if "uiAutomationActivities" in expected:
            actual_ui = actual.get("uiAutomationActivities", 0)
            expected_ui = expected.get("uiAutomationActivities", 0)
            
            if "uiActivitiesRange" in tolerances:
                min_ui, max_ui = tolerances["uiActivitiesRange"]
                if not (min_ui <= actual_ui <= max_ui):
                    print(f"  MISMATCH: UI activities {actual_ui} outside range [{min_ui}, {max_ui}]")
                    all_passed = False
            elif actual_ui != expected_ui:
                print(f"  MISMATCH: UI activities - expected {expected_ui}, got {actual_ui}")
                all_passed = False
        
        # Control structures check
        if "controlStructures" in expected:
            actual_cs = actual.get("controlStructures", {})
            expected_cs = expected.get("controlStructures", {})
            
            for structure, expected_count in expected_cs.items():
                actual_count = actual_cs.get(structure, 0)
                if actual_count != expected_count:
                    print(f"  MISMATCH: {structure} - expected {expected_count}, got {actual_count}")
                    all_passed = False
        
        # Workflow invocations check
        if "workflowInvocations" in expected:
            actual_inv = actual.get("workflowInvocations", 0)
            expected_inv = expected.get("workflowInvocations", 0)
            
            if "invocationRange" in tolerances:
                min_inv, max_inv = tolerances["invocationRange"]
                if not (min_inv <= actual_inv <= max_inv):
                    print(f"  MISMATCH: Workflow invocations {actual_inv} outside range [{min_inv}, {max_inv}]")
                    all_passed = False
            elif actual_inv != expected_inv:
                print(f"  MISMATCH: Workflow invocations - expected {expected_inv}, got {actual_inv}")
                all_passed = False
        
        return all_passed
    
    def _get_activity_type_counts(self, activities: List[Activity]) -> Dict[str, int]:
        """Get count of each activity type."""
        counts = {}
        for activity in activities:
            activity_type = activity.activity_type
            counts[activity_type] = counts.get(activity_type, 0) + 1
        return dict(sorted(counts.items()))
    
    def _get_all_variables_referenced(self, activities: List[Activity]) -> List[str]:
        """Get all unique variables referenced across activities."""
        variables = set()
        for activity in activities:
            variables.update(activity.variables_referenced)
        return sorted(list(variables))
    
    def _extract_key_activities(self, activities: List[Activity]) -> List[Dict[str, Any]]:
        """Extract key activity information for comparison."""
        key_activities = []
        
        for activity in activities:
            key_activity = {
                "activityType": activity.activity_type,
                "displayName": activity.display_name,
                "hasExpressions": len(activity.expressions) > 0,
                "hasArguments": len(activity.arguments) > 0,
                "hasSelectors": len(activity.selectors) > 0,
            }
            
            # Add specific properties based on activity type
            if activity.activity_type == "LogMessage":
                key_activity["level"] = activity.arguments.get("Level", activity.properties.get("Level"))
            
            if activity.activity_type == "If":
                key_activity["hasCondition"] = "Condition" in activity.arguments
            
            if activity.activity_type == "InvokeWorkflowFile":
                key_activity["workflowFileName"] = activity.arguments.get("WorkflowFileName", "")
                key_activity["argumentCount"] = len(activity.arguments)
            
            key_activities.append(key_activity)
        
        return key_activities
    
    def update_golden_results(self, xaml_filename: str) -> bool:
        """Update golden results for a specific test case."""
        print(f"Updating golden results for {xaml_filename}...")
        
        xaml_file = self.test_data_dir / xaml_filename
        golden_file = self.test_data_dir / (xaml_filename.replace('.xaml', '_golden.json'))
        
        if not xaml_file.exists():
            print(f"ERROR: XAML file not found: {xaml_file}")
            return False
        
        # Extract current results
        actual_results = self.extract_test_results(xaml_file)
        if not actual_results:
            print("ERROR: Failed to extract results")
            return False
        
        # Load existing golden file if it exists
        golden_data = {}
        if golden_file.exists():
            try:
                with open(golden_file, 'r', encoding='utf-8') as f:
                    golden_data = json.load(f)
            except Exception as e:
                print(f"WARN: Could not load existing golden file: {e}")
        
        # Update expected results
        golden_data["expectedResults"] = actual_results
        golden_data["lastUpdated"] = str(Path(__file__).stat().st_mtime)
        
        # Write updated golden file
        try:
            with open(golden_file, 'w', encoding='utf-8') as f:
                json.dump(golden_data, f, indent=2, ensure_ascii=False)
            print(f"Updated golden results: {golden_file}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to write golden file: {e}")
            return False


def main():
    """Main entry point for golden freeze testing."""
    parser = argparse.ArgumentParser(description='Golden freeze test system for Activity entity implementation')
    parser.add_argument('--update-golden', nargs='?', const='all', 
                       help='Update golden results (specify filename or "all")')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--test', help='Run specific test case')
    
    args = parser.parse_args()
    
    validator = GoldenFreezeValidator(verbose=args.verbose)
    
    if args.update_golden:
        if args.update_golden == 'all':
            test_files = [
                "simple_sequence.xaml",
                "ui_automation_sample.xaml", 
                "complex_workflow.xaml",
                "invoke_workflows_sample.xaml"
            ]
            for test_file in test_files:
                validator.update_golden_results(test_file)
        else:
            validator.update_golden_results(args.update_golden)
        return
    
    if args.test:
        success = validator.validate_test_case(args.test)
        sys.exit(0 if success else 1)
    
    # Run all tests
    passed, total = validator.run_all_tests()
    
    print(f"\n" + "=" * 50)
    print(f"Golden Freeze Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("OK - All golden freeze tests passed!")
        sys.exit(0)
    else:
        print("ERROR - Some golden freeze tests failed!")
        print("Run with --update-golden to update expected results")
        sys.exit(1)


if __name__ == '__main__':
    main()