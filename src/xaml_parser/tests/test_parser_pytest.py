"""Pytest-style tests for XAML parser core functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock

from xaml_parser import XamlParser, ValidationError, validate_output
from xaml_parser.models import WorkflowContent, WorkflowArgument, Activity


class TestXamlParser:
    """Test cases for XamlParser class using pytest."""
    
    def test_parser_initialization(self):
        """Test parser initialization with default config."""
        parser = XamlParser()
        assert isinstance(parser.config, dict)
        assert parser.config['extract_arguments'] is True
        assert parser.config['expression_language'] == 'VisualBasic'
    
    def test_parser_with_custom_config(self):
        """Test parser initialization with custom configuration."""
        config = {
            'extract_arguments': False,
            'strict_mode': True,
            'max_depth': 50
        }
        parser = XamlParser(config)
        assert parser.config['extract_arguments'] is False
        assert parser.config['strict_mode'] is True
        assert parser.config['max_depth'] == 50
    
    def test_parse_content_success(self, parser, test_xaml):
        """Test successful parsing of XAML content."""
        result = parser.parse_content(test_xaml, "test.xaml")
        
        assert result.success is True
        assert result.content is not None
        assert result.diagnostics is not None
        assert result.file_path == "test.xaml"
        assert result.parse_time_ms >= 0
        
        # Check content structure
        content = result.content
        assert isinstance(content.arguments, list)
        assert isinstance(content.variables, list)
        assert isinstance(content.activities, list)
        assert content.expression_language == 'VisualBasic'
    
    def test_parse_content_with_arguments(self, parser, test_xaml):
        """Test argument extraction from XAML."""
        result = parser.parse_content(test_xaml)
        
        assert result.success is True
        assert len(result.content.arguments) == 1
        
        arg = result.content.arguments[0]
        assert arg.name == "in_TestArg"
        assert arg.direction == "in"
        assert arg.annotation == "Test argument"
    
    def test_parse_content_with_activities(self, parser, test_xaml):
        """Test activity extraction from XAML."""
        result = parser.parse_content(test_xaml)
        
        assert result.success is True
        assert len(result.content.activities) > 0
        
        # Check for Sequence activity
        sequences = [a for a in result.content.activities if a.activity_type == 'Sequence']
        assert len(sequences) > 0
        
        seq = sequences[0]
        assert seq.display_name == "Test Sequence"
        assert seq.annotation == "Test workflow"
    
    def test_parse_invalid_xml(self, parser):
        """Test parsing of malformed XML."""
        invalid_xml = "<Activity><InvalidTag></Activity>"
        result = parser.parse_content(invalid_xml)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "XML parse error" in result.errors[0]
    
    def test_parse_empty_content(self, parser):
        """Test parsing of empty content."""
        result = parser.parse_content("", "empty.xaml")
        
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_diagnostics_collection(self, parser, test_xaml):
        """Test diagnostic information collection."""
        result = parser.parse_content(test_xaml)
        
        assert result.success is True
        assert result.diagnostics is not None
        
        diag = result.diagnostics
        assert diag.total_elements_processed > 0
        assert diag.activities_found > 0
        assert diag.arguments_found == 1
        assert len(diag.processing_steps) > 0
        assert 'xml_parsed' in diag.processing_steps
        assert isinstance(diag.performance_metrics, dict)
    
    def test_strict_mode_validation(self, test_xaml):
        """Test strict mode with validation."""
        parser = XamlParser({'strict_mode': True})
        
        result = parser.parse_content(test_xaml)
        
        # Should still succeed but may have validation warnings
        assert result.success is True
        # Warnings may be added by validation
    
    def test_configuration_preservation(self, test_xaml):
        """Test that configuration is preserved in results."""
        config = {
            'extract_expressions': False,
            'max_depth': 25,
            'strict_mode': True
        }
        parser = XamlParser(config)
        result = parser.parse_content(test_xaml)
        
        assert result.config_used['extract_expressions'] is False
        assert result.config_used['max_depth'] == 25
        assert result.config_used['strict_mode'] is True


class TestParserIntegration:
    """Integration tests with real XAML files."""
    
    @pytest.mark.integration
    def test_corpus_file_parsing(self):
        """Test parsing of corpus project file if available."""
        corpus_path = Path("D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001/Framework/InitAllSettings.xaml")
        
        if not corpus_path.exists():
            pytest.skip("Corpus file not available")
        
        parser = XamlParser()
        result = parser.parse_file(corpus_path)
        
        assert result.success is True
        assert result.content is not None
        assert len(result.content.arguments) == 3  # Known corpus file structure
        assert result.content.root_annotation is not None
        assert len(result.content.activities) > 25
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_large_file_performance(self):
        """Test performance on larger XAML files."""
        corpus_path = Path("D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001/Framework/InitAllSettings.xaml")
        
        if not corpus_path.exists():
            pytest.skip("Corpus file not available")
        
        parser = XamlParser()
        result = parser.parse_file(corpus_path)
        
        assert result.success is True
        assert result.parse_time_ms < 5000  # Should parse in under 5 seconds
        
        # Check diagnostic metrics
        diag = result.diagnostics
        assert diag.file_size_bytes > 10000  # Should be substantial file
        assert diag.total_elements_processed > 100


@pytest.mark.parametrize("config_option,expected_value", [
    ('extract_arguments', True),
    ('extract_variables', True),
    ('extract_activities', True),
    ('strict_mode', False),
    ('max_depth', 100),
    ('expression_language', 'VisualBasic')
])
def test_default_configuration(config_option, expected_value):
    """Test default configuration values."""
    parser = XamlParser()
    assert parser.config[config_option] == expected_value


@pytest.mark.parametrize("invalid_xml,expected_error", [
    ("<Invalid", "XML parse error"),
    ("<Activity><NotClosed></Activity>", "XML parse error"),
    ("", "XML parse error")
])
def test_invalid_xml_handling(parser, invalid_xml, expected_error):
    """Test handling of various invalid XML formats."""
    result = parser.parse_content(invalid_xml)
    assert result.success is False
    assert len(result.errors) > 0
    assert expected_error in result.errors[0]