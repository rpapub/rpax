#!/usr/bin/env python3
"""Test simple schema validation system without external dependencies.

This script validates the schema versioning system, backward compatibility,
and migration capabilities for rpax artifacts using the simple validator.
"""

import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rpax.simple_schema_validator import (
    SimpleArtifactValidator, SchemaVersion, 
    ValidationSeverity, validate_artifact_file
)


def test_schema_version_comparison():
    """Test schema version comparison logic."""
    print("=== Testing Schema Version Comparison ===")
    
    v100 = SchemaVersion("1.0.0")
    v101 = SchemaVersion("1.0.1")
    v110 = SchemaVersion("1.1.0")
    v200 = SchemaVersion("2.0.0")
    
    # Test comparisons
    assert v100 < v101, "Patch version comparison failed"
    assert v101 < v110, "Minor version comparison failed"  
    assert v110 < v200, "Major version comparison failed"
    print("OK - Version comparisons work correctly")
    
    # Test compatibility
    assert v100.is_compatible_with(v101), "Patch compatibility failed"
    assert v100.is_compatible_with(v110), "Minor compatibility failed"
    assert not v100.is_compatible_with(v200), "Major compatibility should fail"
    print("OK - Version compatibility checks work correctly")
    
    return True


def test_valid_activity_artifact():
    """Test validation of a valid activity instances artifact."""
    print("\n=== Testing Valid Activity Artifact ===")
    
    # Create a valid v1.1.0 activity instances artifact
    valid_artifact = {
        "schemaVersion": "1.1.0",
        "workflowId": "test-workflow",
        "projectId": "test-project",
        "totalActivities": 2,
        "visibleActivities": 2,
        "activitiesWithSelectors": 1,
        "activities": [
            {
                "activity_id": "test-project#test-workflow#Activity_1#abc12345",
                "workflow_id": "test-workflow",
                "activity_type": "Sequence",
                "display_name": "Main Sequence",
                "node_id": "Activity_1",
                "parent_activity_id": None,
                "depth": 0,
                "arguments": {"DisplayName": "Main Sequence"},
                "configuration": {},
                "properties": {"DisplayName": "Main Sequence"},
                "metadata": {},
                "expressions": [],
                "variables_referenced": [],
                "selectors": {},
                "annotation": None,
                "is_visible": True,
                "container_type": None,
                "visible_attributes": {},
                "invisible_attributes": {},
                "variables": [],
                "child_activities": [],
                "expression_objects": [],
                "xpath_location": "/Sequence",
                "source_line": None
            },
            {
                "activity_id": "test-project#test-workflow#Activity_2#def67890",
                "workflow_id": "test-workflow", 
                "activity_type": "LogMessage",
                "display_name": "Test Log",
                "node_id": "Activity_2",
                "parent_activity_id": "test-project#test-workflow#Activity_1#abc12345",
                "depth": 1,
                "arguments": {"Message": "[\"Test message\"]", "Level": "Info"},
                "configuration": {},
                "properties": {"Message": "[\"Test message\"]", "Level": "Info"},
                "metadata": {},
                "expressions": ["\"Test message\""],
                "variables_referenced": [],
                "selectors": {"Message": "[\"Test message\"]"},
                "annotation": "Test logging activity",
                "is_visible": True,
                "container_type": "Sequence",
                "visible_attributes": {},
                "invisible_attributes": {},
                "variables": [],
                "child_activities": [],
                "expression_objects": [],
                "xpath_location": "/LogMessage",
                "source_line": 15
            }
        ]
    }
    
    validator = SimpleArtifactValidator()
    result = validator.validate_artifact(valid_artifact, "activity-instances")
    
    if result.is_valid:
        print("OK - Valid artifact passes validation")
        if result.issues:
            for issue in result.issues:
                print(f"  {issue.severity.value.upper()}: {issue.message}")
    else:
        print("ERROR - Valid artifact failed validation")
        for issue in result.issues:
            print(f"  {issue.severity.value.upper()}: {issue.message} at {issue.path}")
        return False
    
    return True


def test_invalid_activity_artifact():
    """Test validation of invalid activity instances artifacts."""
    print("\n=== Testing Invalid Activity Artifacts ===")
    
    validator = SimpleArtifactValidator()
    tests_passed = 0
    
    # Test 1: Missing required fields
    invalid_artifact_1 = {
        "schemaVersion": "1.1.0",
        "workflowId": "test-workflow"
        # Missing projectId, totalActivities, activities
    }
    
    result1 = validator.validate_artifact(invalid_artifact_1, "activity-instances")
    if not result1.is_valid and result1.has_errors:
        print("OK - Missing required fields detected")
        for issue in result1.issues:
            if issue.severity == ValidationSeverity.ERROR:
                print(f"  ERROR: {issue.message}")
        tests_passed += 1
    else:
        print("ERROR - Missing required fields not detected")
    
    # Test 2: Activity count mismatch
    invalid_artifact_2 = {
        "schemaVersion": "1.1.0",
        "workflowId": "test-workflow",
        "projectId": "test-project", 
        "totalActivities": 5,  # Wrong count
        "activities": [{
            "activity_id": "test#test#test#12345678",
            "workflow_id": "test",
            "activity_type": "Test",
            "node_id": "test",
            "depth": 0,
            "arguments": {},
            "configuration": {},
            "properties": {},
            "metadata": {},
            "expressions": [],
            "variables_referenced": [],
            "selectors": {},
            "is_visible": True,
            "visible_attributes": {},
            "invisible_attributes": {},
            "variables": [],
            "child_activities": [],
            "expression_objects": [],
            "xpath_location": None,
            "source_line": None
        }]
    }
    
    result2 = validator.validate_artifact(invalid_artifact_2, "activity-instances")
    if not result2.is_valid and result2.has_errors:
        print("OK - Activity count mismatch detected")
        tests_passed += 1
    else:
        print("ERROR - Activity count mismatch not detected")
    
    # Test 3: Invalid activity ID format
    invalid_artifact_3 = {
        "schemaVersion": "1.1.0",
        "workflowId": "test-workflow",
        "projectId": "test-project",
        "totalActivities": 1,
        "activities": [{
            "activity_id": "invalid-id-format",  # Wrong format
            "workflow_id": "test",
            "activity_type": "Test",
            "node_id": "test",
            "depth": 0,
            "arguments": {},
            "configuration": {},
            "properties": {},
            "metadata": {},
            "expressions": [],
            "variables_referenced": [],
            "selectors": {},
            "is_visible": True,
            "visible_attributes": {},
            "invisible_attributes": {},
            "variables": [],
            "child_activities": [],
            "expression_objects": [],
            "xpath_location": None,
            "source_line": None
        }]
    }
    
    result3 = validator.validate_artifact(invalid_artifact_3, "activity-instances")
    if not result3.is_valid and result3.has_errors:
        print("OK - Invalid activity ID format detected")
        tests_passed += 1
    else:
        print("ERROR - Invalid activity ID format not detected")
    
    return tests_passed == 3


def test_backward_compatibility():
    """Test backward compatibility validation."""
    print("\n=== Testing Backward Compatibility ===")
    
    validator = SimpleArtifactValidator()
    
    # Create a v1.0.0 artifact (without new v1.1.0 fields)
    v1_artifact = {
        "schemaVersion": "1.0.0",
        "workflowId": "test-workflow",
        "totalActivities": 1,
        "activities": [{
            "activity_id": "test#test#test#12345678",
            "workflow_id": "test",
            "activity_type": "Test",
            "node_id": "test",
            "depth": 0,
            "arguments": {},
            "configuration": {},
            "properties": {},
            "metadata": {},
            "expressions": [],
            "variables_referenced": [],
            "selectors": {},
            "is_visible": True,
            "visible_attributes": {},
            "invisible_attributes": {},
            "variables": [],
            "child_activities": [],
            "expression_objects": [],
            "xpath_location": None,
            "source_line": None
        }]
    }
    
    # Should validate successfully with appropriate warnings
    result = validator.validate_artifact(v1_artifact, "activity-instances")
    
    if result.is_valid:
        print("OK - v1.0.0 artifact validates successfully")
        if result.has_warnings:
            print("  - Warnings present as expected for version compatibility")
            for issue in result.issues:
                if issue.severity == ValidationSeverity.WARNING:
                    print(f"    WARN: {issue.message}")
    else:
        print("ERROR - v1.0.0 artifact failed validation")
        for issue in result.issues:
            if issue.severity == ValidationSeverity.ERROR:
                print(f"    ERROR: {issue.message}")
        return False
    
    # Test compatibility checking
    is_compatible, issues = validator.validate_compatibility("1.0.0", "1.1.0", "activity-instances")
    if is_compatible:
        print("OK - v1.0.0 to v1.1.0 upgrade is compatible")
        for issue in issues:
            print(f"  INFO: {issue}")
    else:
        print("ERROR - v1.0.0 to v1.1.0 should be compatible")
        return False
    
    # Test incompatible version jump
    is_compatible, issues = validator.validate_compatibility("1.0.0", "2.0.0", "activity-instances")  
    if not is_compatible:
        print("OK - v1.0.0 to v2.0.0 upgrade correctly identified as incompatible")
        for issue in issues:
            print(f"  INFO: {issue}")
    else:
        print("ERROR - v1.0.0 to v2.0.0 should be incompatible")
        return False
    
    return True


def test_migration_guidance():
    """Test migration guide generation."""
    print("\n=== Testing Migration Guidance ===")
    
    validator = SimpleArtifactValidator()
    
    # Generate migration guide for v1.0.0 to v1.1.0
    migration_steps = validator.generate_migration_guide("1.0.0", "1.1.0", "activity-instances")
    
    if migration_steps:
        print("OK - Migration guide generated")
        print("  Migration steps:")
        for i, step in enumerate(migration_steps, 1):
            print(f"    {i}. {step}")
    else:
        print("WARN - No migration steps generated")
    
    return True


def test_real_artifact_validation():
    """Test validation against real generated artifacts."""
    print("\n=== Testing Real Artifact Validation ===")
    
    # Check for any generated activity instances artifacts
    test_outputs = list(Path(".").glob("test_output_*.json"))
    
    if not test_outputs:
        print("INFO - No real artifacts found to validate")
        return True
    
    validated_count = 0
    valid_count = 0
    
    for output_file in test_outputs[:3]:  # Test first 3 files
        print(f"Validating {output_file.name}...")
        
        try:
            result = validate_artifact_file(output_file, "activity-instances")
            
            if result.is_valid:
                print(f"  OK - {output_file.name} is valid")
                valid_count += 1
                if result.issues:
                    for issue in result.issues:
                        if issue.severity in [ValidationSeverity.WARNING, ValidationSeverity.INFO]:
                            print(f"    {issue.severity.value.upper()}: {issue.message}")
            else:
                print(f"  ERROR - {output_file.name} validation failed")
                for issue in result.issues[:3]:  # Show first 3 errors
                    if issue.severity == ValidationSeverity.ERROR:
                        print(f"    ERROR: {issue.message} at {issue.path}")
            
            validated_count += 1
            
        except Exception as e:
            print(f"  ERROR - Failed to validate {output_file.name}: {e}")
    
    print(f"Validated {validated_count}/{len(test_outputs)} real artifacts ({valid_count} valid)")
    return validated_count > 0


def main():
    """Run all simple schema validation tests."""
    print("Testing Simple Schema Validation System")
    print("=" * 50)
    
    tests = [
        ("Schema Version Comparison", test_schema_version_comparison),
        ("Valid Activity Artifact", test_valid_activity_artifact),
        ("Invalid Activity Artifacts", test_invalid_activity_artifact),
        ("Backward Compatibility", test_backward_compatibility),
        ("Migration Guidance", test_migration_guidance),
        ("Real Artifact Validation", test_real_artifact_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"PASS: {test_name}")
            else:
                print(f"FAIL: {test_name}")
        except Exception as e:
            print(f"EXCEPTION: {test_name} - {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n" + "=" * 50)
    print(f"Schema Validation Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("OK - All schema validation tests passed!")
        return True
    else:
        print("ERROR - Some schema validation tests failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)