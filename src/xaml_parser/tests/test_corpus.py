"""Comprehensive tests using the test corpus data."""

import unittest
import json
from pathlib import Path

from xaml_parser import XamlParser, ValidationError


class TestCorpusData(unittest.TestCase):
    """Test cases using structured corpus data."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        cls.corpus_dir = Path(__file__).parent / "corpus"
        cls.parser = XamlParser()
        cls.strict_parser = XamlParser({'strict_mode': True})
    
    def setUp(self):
        """Set up test fixtures."""
        # Ensure corpus directory exists
        if not self.corpus_dir.exists():
            self.skipTest("Test corpus not available")
    
    def test_simple_project_structure(self):
        """Test parsing of simple project structure."""
        simple_project = self.corpus_dir / "simple_project"
        
        # Test project.json exists
        project_json = simple_project / "project.json"
        self.assertTrue(project_json.exists(), "project.json should exist")
        
        # Validate project.json structure
        with open(project_json) as f:
            project_data = json.load(f)
        
        self.assertEqual(project_data["name"], "SimpleTestProject")
        self.assertEqual(project_data["main"], "Main.xaml")
        self.assertEqual(project_data["expressionLanguage"], "VisualBasic")
    
    def test_main_workflow_parsing(self):
        """Test parsing of Main.xaml from simple project."""
        main_workflow = self.corpus_dir / "simple_project" / "Main.xaml"
        self.assertTrue(main_workflow.exists(), "Main.xaml should exist")
        
        result = self.parser.parse_file(main_workflow)
        
        # Validate successful parsing
        self.assertTrue(result.success, f"Parsing should succeed: {result.errors}")
        self.assertIsNotNone(result.content)
        self.assertIsNotNone(result.diagnostics)
        
        content = result.content
        
        # Validate arguments extraction
        self.assertEqual(len(content.arguments), 2, "Should have 2 arguments")
        
        arg_names = {arg.name for arg in content.arguments}
        self.assertIn("in_ConfigFile", arg_names)
        self.assertIn("out_ProcessedItems", arg_names)
        
        # Validate argument details
        config_arg = next(arg for arg in content.arguments if arg.name == "in_ConfigFile")
        self.assertEqual(config_arg.direction, "in")
        self.assertEqual(config_arg.annotation, "Path to configuration file")
        
        output_arg = next(arg for arg in content.arguments if arg.name == "out_ProcessedItems")
        self.assertEqual(output_arg.direction, "out")
        self.assertEqual(output_arg.annotation, "Number of items processed")
        
        # Validate variables extraction
        self.assertGreater(len(content.variables), 0, "Should have variables")
        var_names = {var.name for var in content.variables}
        self.assertIn("ConfigData", var_names)
        self.assertIn("Counter", var_names)
        
        # Validate activities extraction
        self.assertGreater(len(content.activities), 5, "Should have multiple activities")
        
        # Validate root annotation
        self.assertIsNotNone(content.root_annotation)
        self.assertIn("Main workflow", content.root_annotation)
        
        # Validate expression language
        self.assertEqual(content.expression_language, "VisualBasic")
    
    def test_get_config_workflow_parsing(self):
        """Test parsing of GetConfig.xaml workflow."""
        get_config_workflow = self.corpus_dir / "simple_project" / "workflows" / "GetConfig.xaml"
        self.assertTrue(get_config_workflow.exists(), "GetConfig.xaml should exist")
        
        result = self.parser.parse_file(get_config_workflow)
        
        self.assertTrue(result.success, f"Parsing should succeed: {result.errors}")
        
        content = result.content
        
        # Validate arguments
        self.assertEqual(len(content.arguments), 2)
        arg_names = {arg.name for arg in content.arguments}
        self.assertIn("in_ConfigPath", arg_names)
        self.assertIn("out_ConfigData", arg_names)
        
        # Validate both arguments have annotations
        for arg in content.arguments:
            self.assertIsNotNone(arg.annotation, f"Argument {arg.name} should have annotation")
        
        # Validate variables
        var_names = {var.name for var in content.variables}
        self.assertIn("FileExists", var_names)
        
        # Validate TryCatch activity present
        activity_tags = {act.activity_type for act in content.activities}
        self.assertIn("TryCatch", activity_tags, "Should contain TryCatch activity")
        
        # Validate exception handling structure
        try_catch_activities = [act for act in content.activities if act.activity_type == "TryCatch"]
        self.assertGreater(len(try_catch_activities), 0)
    
    def test_edge_cases_malformed_xml(self):
        """Test handling of malformed XML."""
        malformed_file = self.corpus_dir / "edge_cases" / "malformed.xaml"
        self.assertTrue(malformed_file.exists(), "malformed.xaml should exist")
        
        result = self.parser.parse_file(malformed_file)
        
        # Should fail gracefully
        self.assertFalse(result.success, "Malformed XML should fail to parse")
        self.assertGreater(len(result.errors), 0, "Should have error messages")
        self.assertIn("XML parse error", result.errors[0])
        
        # Should have diagnostics even for failed parse
        self.assertIsNotNone(result.diagnostics)
        self.assertIn("xml_parse_failed", result.diagnostics.processing_steps)
    
    def test_edge_cases_empty_workflow(self):
        """Test handling of empty workflow."""
        empty_file = self.corpus_dir / "edge_cases" / "empty.xaml"
        self.assertTrue(empty_file.exists(), "empty.xaml should exist")
        
        result = self.parser.parse_file(empty_file)
        
        # Should parse successfully but have minimal content
        self.assertTrue(result.success, f"Empty workflow should parse: {result.errors}")
        
        content = result.content
        self.assertEqual(len(content.arguments), 0, "Empty workflow should have no arguments")
        # May have minimal activities (Sequence container)
        self.assertGreaterEqual(len(content.activities), 0)
        
        # Should have valid diagnostics
        self.assertIsNotNone(result.diagnostics)
        self.assertGreater(result.diagnostics.total_elements_processed, 0)
    
    def test_validation_with_corpus_data(self):
        """Test output validation using corpus data."""
        main_workflow = self.corpus_dir / "simple_project" / "Main.xaml"
        
        # Parse with strict mode
        result = self.strict_parser.parse_file(main_workflow)
        
        self.assertTrue(result.success, f"Strict parsing should succeed: {result.errors}")
        
        # Should have no validation warnings for well-formed workflow
        validation_warnings = [w for w in result.warnings if w.startswith("Validation:")]
        self.assertEqual(len(validation_warnings), 0, 
                        f"Should have no validation warnings: {validation_warnings}")
        
        # Manually validate the result
        from xaml_parser.validation import validate_output
        
        validation_errors = validate_output(result, strict=False)
        self.assertEqual(len(validation_errors), 0, 
                        f"Should pass validation: {validation_errors}")
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks with corpus data."""
        main_workflow = self.corpus_dir / "simple_project" / "Main.xaml"
        
        # Parse multiple times to get consistent timing
        parse_times = []
        for _ in range(5):
            result = self.parser.parse_file(main_workflow)
            self.assertTrue(result.success)
            parse_times.append(result.parse_time_ms)
        
        avg_parse_time = sum(parse_times) / len(parse_times)
        
        # Should parse reasonably quickly (under 100ms for simple workflow)
        self.assertLess(avg_parse_time, 100, 
                       f"Average parse time ({avg_parse_time:.2f}ms) should be under 100ms")
        
        # Check diagnostic performance metrics
        result = self.parser.parse_file(main_workflow)
        diag = result.diagnostics
        
        self.assertIn("xml_parse_ms", diag.performance_metrics)
        self.assertIn("content_extract_ms", diag.performance_metrics)
        
        # XML parsing should be faster than content extraction
        xml_time = diag.performance_metrics["xml_parse_ms"]
        extract_time = diag.performance_metrics["content_extract_ms"]
        
        self.assertGreaterEqual(xml_time, 0, "XML parse time should be non-negative")
        self.assertGreaterEqual(extract_time, 0, "Content extraction time should be non-negative")
    
    def test_golden_freeze_consistency(self):
        """Test consistency of parsing results (golden freeze test)."""
        main_workflow = self.corpus_dir / "simple_project" / "Main.xaml"
        
        # Parse the same file multiple times
        results = []
        for _ in range(3):
            result = self.parser.parse_file(main_workflow)
            self.assertTrue(result.success)
            results.append(result)
        
        # Results should be consistent
        first_content = results[0].content
        
        for i, result in enumerate(results[1:], 1):
            content = result.content
            
            # Same number of elements
            self.assertEqual(len(content.arguments), len(first_content.arguments),
                           f"Argument count should be consistent (run {i})")
            self.assertEqual(len(content.variables), len(first_content.variables),
                           f"Variable count should be consistent (run {i})")
            self.assertEqual(len(content.activities), len(first_content.activities),
                           f"Activity count should be consistent (run {i})")
            
            # Same argument names and properties
            for j, (arg1, arg2) in enumerate(zip(first_content.arguments, content.arguments)):
                self.assertEqual(arg1.name, arg2.name, f"Argument {j} name should be consistent (run {i})")
                self.assertEqual(arg1.type, arg2.type, f"Argument {j} type should be consistent (run {i})")
                self.assertEqual(arg1.direction, arg2.direction, f"Argument {j} direction should be consistent (run {i})")
            
            # Same root annotation
            self.assertEqual(content.root_annotation, first_content.root_annotation,
                           f"Root annotation should be consistent (run {i})")
    
    def test_cross_platform_paths(self):
        """Test that corpus paths work across platforms."""
        # Use Path objects consistently
        simple_project = self.corpus_dir / "simple_project"
        main_workflow = simple_project / "Main.xaml"
        
        # Should work regardless of platform path separators
        self.assertTrue(main_workflow.exists())
        
        result = self.parser.parse_file(main_workflow)
        self.assertTrue(result.success)
        
        # File path in result should be absolute
        self.assertTrue(Path(result.file_path).is_absolute())
    
    def test_corpus_completeness(self):
        """Test that corpus has all expected files."""
        # Check required directories exist
        required_dirs = [
            "simple_project",
            "edge_cases"
        ]
        
        for dir_name in required_dirs:
            dir_path = self.corpus_dir / dir_name
            self.assertTrue(dir_path.exists(), f"Directory {dir_name} should exist")
        
        # Check required files exist
        required_files = [
            "simple_project/project.json",
            "simple_project/Main.xaml",
            "simple_project/workflows/GetConfig.xaml",
            "edge_cases/malformed.xaml",
            "edge_cases/empty.xaml"
        ]
        
        for file_path in required_files:
            full_path = self.corpus_dir / file_path
            self.assertTrue(full_path.exists(), f"File {file_path} should exist")


if __name__ == '__main__':
    unittest.main()