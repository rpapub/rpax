"""Tests for output validation functionality."""

import unittest
from unittest.mock import Mock

from xaml_parser import ValidationError, validate_output, OutputValidator
from xaml_parser.models import (
    WorkflowContent, WorkflowArgument, WorkflowVariable, 
    Activity, Expression, ParseResult, ParseDiagnostics
)


class TestOutputValidation(unittest.TestCase):
    """Test cases for output validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = OutputValidator()
        
        # Create valid test data
        self.valid_argument = WorkflowArgument(
            name="test_arg",
            type="InArgument(x:String)",
            direction="in",
            annotation="Test annotation"
        )
        
        self.valid_variable = WorkflowVariable(
            name="test_var",
            type="x:String",
            scope="workflow"
        )
        
        # Create mock object with old structure for validator compatibility
        from unittest.mock import Mock
        self.valid_activity = Mock()
        self.valid_activity.tag = "Sequence"
        self.valid_activity.activity_id = "activity_1"
        self.valid_activity.display_name = "Test Sequence"
        self.valid_activity.visible_attributes = {"DisplayName": "Test"}
        self.valid_activity.invisible_attributes = {}
        self.valid_activity.configuration = {}
        self.valid_activity.variables = []
        self.valid_activity.expressions = []
        self.valid_activity.child_activities = []
        self.valid_activity.depth_level = 0
        
        self.valid_content = WorkflowContent(
            arguments=[self.valid_argument],
            variables=[self.valid_variable],
            activities=[self.valid_activity],
            expression_language="VisualBasic",
            total_activities=1,
            total_arguments=1,
            total_variables=1
        )
        
        self.valid_diagnostics = ParseDiagnostics(
            total_elements_processed=10,
            activities_found=1,
            arguments_found=1,
            variables_found=1,
            annotations_found=1,
            expressions_found=0,
            namespaces_detected=3,
            skipped_elements=0,
            xml_depth=5,
            file_size_bytes=1024,
            processing_steps=["parse_started", "content_extracted"],
            performance_metrics={"xml_parse_ms": 1.0, "extract_ms": 2.0}
        )
        
        self.valid_result = ParseResult(
            content=self.valid_content,
            success=True,
            errors=[],
            warnings=[],
            parse_time_ms=5.0,
            file_path="test.xaml",
            diagnostics=self.valid_diagnostics,
            config_used={
                "extract_arguments": True,
                "extract_variables": True,
                "extract_activities": True,
                "strict_mode": False,
                "max_depth": 100,
                "expression_language": "VisualBasic"
            }
        )
    
    def test_valid_parse_result(self):
        """Test validation of completely valid parse result."""
        errors = self.validator.validate_parse_result(self.valid_result)
        self.assertEqual(len(errors), 0, f"Valid result should have no errors: {errors}")
    
    def test_invalid_success_field(self):
        """Test validation with invalid success field."""
        result = ParseResult(
            success="not_boolean",  # Invalid type
            errors=[],
            warnings=[],
            parse_time_ms=5.0,
            config_used={}
        )
        
        errors = self.validator.validate_parse_result(result)
        self.assertIn("ParseResult.success must be boolean", errors)
    
    def test_invalid_parse_time(self):
        """Test validation with invalid parse time."""
        result = ParseResult(
            success=True,
            errors=[],
            warnings=[],
            parse_time_ms=-1.0,  # Invalid negative time
            config_used={}
        )
        
        errors = self.validator.validate_parse_result(result)
        self.assertIn("ParseResult.parse_time_ms must be non-negative number", errors)
    
    def test_invalid_errors_list(self):
        """Test validation with invalid errors list."""
        result = ParseResult(
            success=True,
            errors=["valid error", "", "   "],  # Contains empty strings
            warnings=[],
            parse_time_ms=5.0,
            config_used={}
        )
        
        errors = self.validator.validate_parse_result(result)
        self.assertIn("ParseResult.errors must contain non-empty strings", errors)
    
    def test_workflow_content_validation(self):
        """Test validation of workflow content structure."""
        errors = self.validator.validate_workflow_content(self.valid_content)
        self.assertEqual(len(errors), 0, f"Valid content should have no errors: {errors}")
    
    def test_invalid_expression_language(self):
        """Test validation with invalid expression language."""
        content = WorkflowContent(
            arguments=[],
            variables=[],
            activities=[],
            expression_language="InvalidLanguage",  # Invalid language
            total_activities=0,
            total_arguments=0,
            total_variables=0
        )
        
        errors = self.validator.validate_workflow_content(content)
        self.assertIn("expression_language must be 'VisualBasic' or 'CSharp'", errors)
    
    def test_mismatched_counts(self):
        """Test validation with mismatched count fields."""
        content = WorkflowContent(
            arguments=[self.valid_argument],
            variables=[],
            activities=[],
            expression_language="VisualBasic",
            total_activities=5,  # Mismatched count
            total_arguments=10,  # Mismatched count  
            total_variables=0
        )
        
        errors = self.validator.validate_workflow_content(content)
        self.assertIn("total_activities (5) != len(activities) (0)", errors)
        self.assertIn("total_arguments (10) != len(arguments) (1)", errors)
    
    def test_argument_validation(self):
        """Test validation of individual arguments."""
        # Invalid argument with missing name
        invalid_arg = Mock()
        invalid_arg.name = ""  # Empty name
        invalid_arg.type = "InArgument(x:String)"
        invalid_arg.direction = "in"
        
        errors = self.validator._validate_argument(invalid_arg)
        self.assertIn("name must be non-empty string", errors)
    
    def test_invalid_argument_direction(self):
        """Test validation with invalid argument direction."""
        invalid_arg = Mock()
        invalid_arg.name = "test_arg"
        invalid_arg.type = "InArgument(x:String)"
        invalid_arg.direction = "invalid_direction"  # Invalid direction
        
        errors = self.validator._validate_argument(invalid_arg)
        self.assertIn("direction must be 'in', 'out', or 'inout'", errors)
    
    def test_activity_validation(self):
        """Test validation of individual activities."""
        activity_ids = set()
        errors = self.validator._validate_activity(self.valid_activity, activity_ids)
        self.assertEqual(len(errors), 0)
        self.assertIn("activity_1", activity_ids)
    
    def test_duplicate_activity_ids(self):
        """Test validation with duplicate activity IDs."""
        activity_ids = {"activity_1"}  # Pre-existing ID
        
        errors = self.validator._validate_activity(self.valid_activity, activity_ids)
        self.assertIn("duplicate activity_id 'activity_1'", errors)
    
    def test_invalid_activity_id_pattern(self):
        """Test validation with invalid activity ID pattern."""
        invalid_activity = Mock()
        invalid_activity.tag = "Sequence"
        invalid_activity.activity_id = "invalid_id"  # Doesn't match pattern
        invalid_activity.visible_attributes = {}
        invalid_activity.invisible_attributes = {}
        invalid_activity.configuration = {}
        invalid_activity.variables = []
        invalid_activity.expressions = []
        invalid_activity.child_activities = []
        invalid_activity.depth_level = 0
        
        errors = self.validator._validate_activity(invalid_activity, set())
        self.assertIn("activity_id must match pattern 'activity_\\d+'", errors)
    
    def test_diagnostics_validation(self):
        """Test validation of diagnostic information."""
        errors = self.validator.validate_diagnostics(self.valid_diagnostics)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_diagnostics_integers(self):
        """Test validation with invalid diagnostic integer fields."""
        invalid_diag = ParseDiagnostics(
            total_elements_processed=-1,  # Invalid negative
            activities_found="not_int",   # Invalid type
            arguments_found=1,
            variables_found=1,
            annotations_found=1,
            expressions_found=1,
            namespaces_detected=1,
            skipped_elements=1,
            xml_depth=1,
            file_size_bytes=1,
            processing_steps=[],
            performance_metrics={}
        )
        
        errors = self.validator.validate_diagnostics(invalid_diag)
        self.assertIn("total_elements_processed must be non-negative integer", errors)
    
    def test_invalid_performance_metrics(self):
        """Test validation with invalid performance metrics."""
        invalid_diag = ParseDiagnostics(
            total_elements_processed=1,
            activities_found=1,
            arguments_found=1,
            variables_found=1,
            annotations_found=1,
            expressions_found=1,
            namespaces_detected=1,
            skipped_elements=1,
            xml_depth=1,
            file_size_bytes=1,
            processing_steps=[],
            performance_metrics={
                "invalid_metric": 5.0,      # Should end with _ms
                "parse_ms": -1.0            # Should be non-negative
            }
        )
        
        errors = self.validator.validate_diagnostics(invalid_diag)
        self.assertIn("performance_metrics key 'invalid_metric' must end with '_ms'", errors)
        self.assertIn("performance_metrics['parse_ms'] must be non-negative number", errors)
    
    def test_config_validation(self):
        """Test validation of parser configuration."""
        valid_config = {
            "extract_arguments": True,
            "extract_variables": False,
            "extract_activities": True,
            "strict_mode": False,
            "max_depth": 50,
            "expression_language": "CSharp"
        }
        
        errors = self.validator.validate_config(valid_config)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_config_types(self):
        """Test validation with invalid configuration types."""
        invalid_config = {
            "extract_arguments": "not_boolean",     # Should be boolean
            "max_depth": -5,                       # Should be positive
            "expression_language": "InvalidLang"   # Should be valid language
        }
        
        errors = self.validator.validate_config(invalid_config)
        self.assertIn("extract_arguments must be boolean", errors)
        self.assertIn("max_depth must be positive integer", errors)
        self.assertIn("expression_language must be 'VisualBasic' or 'CSharp'", errors)
    
    def test_validate_output_function(self):
        """Test the validate_output convenience function."""
        # Should not raise exception for valid result
        errors = validate_output(self.valid_result, strict=False)
        self.assertEqual(len(errors), 0)
        
        # Should not raise exception in non-strict mode
        try:
            validate_output(self.valid_result, strict=False)
        except ValidationError:
            self.fail("validate_output should not raise in non-strict mode for valid data")
    
    def test_validate_output_strict_mode(self):
        """Test strict mode validation with invalid data."""
        invalid_result = ParseResult(
            success="not_boolean",  # Invalid
            errors=[],
            warnings=[],
            parse_time_ms=5.0,
            config_used={}
        )
        
        # Should raise exception in strict mode
        with self.assertRaises(ValidationError) as ctx:
            validate_output(invalid_result, strict=True)
        
        self.assertIn("validation failed", str(ctx.exception).lower())
        self.assertGreater(len(ctx.exception.schema_violations), 0)


if __name__ == '__main__':
    unittest.main()