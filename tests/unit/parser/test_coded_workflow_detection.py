"""Tests for Issue-62: Handle coded workflows (.cs) invocations."""

import pytest
from pathlib import Path
from rpax.parser.xaml_analyzer import XamlAnalyzer


class TestCodedWorkflowDetection:
    """Test detection of coded workflow invocations."""

    def setup_method(self):
        """Set up test analyzer."""
        self.analyzer = XamlAnalyzer()

    def test_determine_invocation_kind_coded_workflow(self):
        """Test that .cs files are classified as invoke-coded."""
        # Create a dummy XAML path for context
        xaml_path = Path("/test/workflow.xaml")
        
        # Test coded workflow detection
        result = self.analyzer._determine_invocation_kind("Framework/InitAllApplications.cs", xaml_path)
        assert result == "invoke-coded"
        
        # Test with different path formats
        result = self.analyzer._determine_invocation_kind("Framework\\InitAllApplications.cs", xaml_path)
        assert result == "invoke-coded"
        
        result = self.analyzer._determine_invocation_kind("MyCodedWorkflow.cs", xaml_path)
        assert result == "invoke-coded"

    def test_determine_invocation_kind_case_insensitive(self):
        """Test that coded workflow detection is case insensitive."""
        xaml_path = Path("/test/workflow.xaml")
        
        # Test uppercase extension
        result = self.analyzer._determine_invocation_kind("Framework/InitAllApplications.CS", xaml_path)
        assert result == "invoke-coded"
        
        # Test mixed case
        result = self.analyzer._determine_invocation_kind("Framework/InitAllApplications.Cs", xaml_path)
        assert result == "invoke-coded"

    def test_determine_invocation_kind_still_detects_other_types(self):
        """Test that other invocation types still work correctly."""
        xaml_path = Path("/test/workflow.xaml")
        
        # Dynamic invocations should still work
        result = self.analyzer._determine_invocation_kind("Path.Combine(folder, file)", xaml_path)
        assert result == "invoke-dynamic"
        
        result = self.analyzer._determine_invocation_kind("{variableName}", xaml_path)
        assert result == "invoke-dynamic"
        
        # Missing XAML files should still be detected as invoke-missing
        result = self.analyzer._determine_invocation_kind("NonExistent.xaml", xaml_path)
        assert result == "invoke-missing"

    def test_integration_with_frozenchlorine_example(self):
        """Test against the actual FrozenChlorine coded workflow invocation."""
        # Test the exact invocation from FrozenChlorine
        xaml_path = Path("D:/github.com/rpapub/FrozenChlorine/RnD/RnD_InvokeCodedWorkflow.xaml")
        
        result = self.analyzer._determine_invocation_kind("Framework\\InitAllApplications.cs", xaml_path)
        assert result == "invoke-coded"
        
        # Verify the classification is consistent
        result2 = self.analyzer._determine_invocation_kind("Framework/InitAllApplications.cs", xaml_path)
        assert result2 == "invoke-coded"
        assert result == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])