"""Tests for XAML parser core functionality."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from xaml_parser import XamlParser, ValidationError, validate_output
from xaml_parser.models import WorkflowContent, WorkflowArgument, Activity


class TestXamlParser(unittest.TestCase):
    """Test cases for XamlParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = XamlParser()
        self.test_xaml = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <x:Members>
    <x:Property Name="in_TestArg" Type="InArgument(x:String)" sap2010:Annotation.AnnotationText="Test argument" />
  </x:Members>
  <Sequence DisplayName="Test Sequence" sap2010:Annotation.AnnotationText="Test workflow">
    <LogMessage DisplayName="Log Test" Text="Hello World" />
  </Sequence>
</Activity>"""
    
    def test_parser_initialization(self):
        """Test parser initialization with default config."""
        parser = XamlParser()
        self.assertIsInstance(parser.config, dict)
        self.assertTrue(parser.config['extract_arguments'])
        self.assertEqual(parser.config['expression_language'], 'VisualBasic')
    
    def test_parser_with_custom_config(self):
        """Test parser initialization with custom configuration."""
        config = {
            'extract_arguments': False,
            'strict_mode': True,
            'max_depth': 50
        }
        parser = XamlParser(config)
        self.assertFalse(parser.config['extract_arguments'])
        self.assertTrue(parser.config['strict_mode'])
        self.assertEqual(parser.config['max_depth'], 50)
    
    def test_parse_content_success(self):
        """Test successful parsing of XAML content."""
        result = self.parser.parse_content(self.test_xaml, "test.xaml")
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.content)
        self.assertIsNotNone(result.diagnostics)
        self.assertEqual(result.file_path, "test.xaml")
        self.assertGreaterEqual(result.parse_time_ms, 0)
        
        # Check content structure
        content = result.content
        self.assertIsInstance(content.arguments, list)
        self.assertIsInstance(content.variables, list)
        self.assertIsInstance(content.activities, list)
        self.assertEqual(content.expression_language, 'VisualBasic')
    
    def test_parse_content_with_arguments(self):
        """Test argument extraction from XAML."""
        result = self.parser.parse_content(self.test_xaml)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.content.arguments), 1)
        
        arg = result.content.arguments[0]
        self.assertEqual(arg.name, "in_TestArg")
        self.assertEqual(arg.direction, "in")
        self.assertEqual(arg.annotation, "Test argument")
    
    def test_parse_content_with_activities(self):
        """Test activity extraction from XAML."""
        result = self.parser.parse_content(self.test_xaml)
        
        self.assertTrue(result.success)
        self.assertGreater(len(result.content.activities), 0)
        
        # Check for Sequence activity
        sequences = [a for a in result.content.activities if a.activity_type == 'Sequence']
        self.assertGreater(len(sequences), 0)
        
        seq = sequences[0]
        self.assertEqual(seq.display_name, "Test Sequence")
        self.assertEqual(seq.annotation, "Test workflow")
    
    def test_parse_invalid_xml(self):
        """Test parsing of malformed XML."""
        invalid_xml = "<Activity><InvalidTag></Activity>"
        result = self.parser.parse_content(invalid_xml)
        
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("XML parse error", result.errors[0])
    
    def test_parse_empty_content(self):
        """Test parsing of empty content."""
        result = self.parser.parse_content("", "empty.xaml")
        
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
    
    def test_diagnostics_collection(self):
        """Test diagnostic information collection."""
        result = self.parser.parse_content(self.test_xaml)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.diagnostics)
        
        diag = result.diagnostics
        self.assertGreater(diag.total_elements_processed, 0)
        self.assertGreater(diag.activities_found, 0)
        self.assertEqual(diag.arguments_found, 1)
        self.assertGreater(len(diag.processing_steps), 0)
        self.assertIn('xml_parsed', diag.processing_steps)
        self.assertIsInstance(diag.performance_metrics, dict)
    
    def test_strict_mode_validation(self):
        """Test strict mode with validation."""
        config = {'strict_mode': True}
        parser = XamlParser(config)
        
        result = parser.parse_content(self.test_xaml)
        
        # Should still succeed but may have validation warnings
        self.assertTrue(result.success)
        # Warnings may be added by validation
    
    def test_configuration_preservation(self):
        """Test that configuration is preserved in results."""
        config = {
            'extract_expressions': False,
            'max_depth': 25,
            'strict_mode': True
        }
        parser = XamlParser(config)
        result = parser.parse_content(self.test_xaml)
        
        self.assertEqual(result.config_used['extract_expressions'], False)
        self.assertEqual(result.config_used['max_depth'], 25)
        self.assertEqual(result.config_used['strict_mode'], True)


class TestParserIntegration(unittest.TestCase):
    """Integration tests with real XAML files."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.parser = XamlParser()
        # Use corpus project if available
        self.corpus_path = Path("D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001/Framework/InitAllSettings.xaml")
    
    def test_corpus_file_parsing(self):
        """Test parsing of corpus project file if available."""
        if not self.corpus_path.exists():
            self.skipTest("Corpus file not available")
        
        result = self.parser.parse_file(self.corpus_path)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.content)
        self.assertEqual(len(result.content.arguments), 3)  # Known corpus file structure
        self.assertIsNotNone(result.content.root_annotation)
        self.assertGreater(len(result.content.activities), 25)
    
    def test_large_file_performance(self):
        """Test performance on larger XAML files."""
        if not self.corpus_path.exists():
            self.skipTest("Corpus file not available")
        
        result = self.parser.parse_file(self.corpus_path)
        
        self.assertTrue(result.success)
        self.assertLess(result.parse_time_ms, 5000)  # Should parse in under 5 seconds
        
        # Check diagnostic metrics
        diag = result.diagnostics
        self.assertGreater(diag.file_size_bytes, 10000)  # Should be substantial file
        self.assertGreater(diag.total_elements_processed, 100)


if __name__ == '__main__':
    unittest.main()