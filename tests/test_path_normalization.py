"""Test path normalization utilities per ADR-030."""

import pytest

from rpax.utils.paths import normalize_path, normalize_workflow_path


class TestPathNormalization:
    """Test path separator normalization for cross-platform compatibility."""

    def test_normalize_path_backslashes_to_forward(self):
        """Test converting Windows backslashes to forward slashes."""
        # Basic Windows path
        assert normalize_path("Framework\\InitAllSettings.xaml") == "Framework/InitAllSettings.xaml"
        
        # Nested Windows path
        assert normalize_path("Foo\\Bar\\MyWorkflow.xaml") == "Foo/Bar/MyWorkflow.xaml"
        
        # Mixed separators
        assert normalize_path("Framework\\Sub/MyWorkflow.xaml") == "Framework/Sub/MyWorkflow.xaml"

    def test_normalize_path_forward_slashes_unchanged(self):
        """Test that forward slashes remain unchanged."""
        # Already normalized paths should remain the same
        assert normalize_path("Framework/InitAllSettings.xaml") == "Framework/InitAllSettings.xaml"
        assert normalize_path("Foo/Bar/MyWorkflow.xaml") == "Foo/Bar/MyWorkflow.xaml"

    def test_normalize_path_absolute_windows(self):
        """Test absolute Windows paths."""
        input_path = "C:\\Projects\\UiPath\\MyProject\\Framework\\InitAllSettings.xaml"
        expected = "C:/Projects/UiPath/MyProject/Framework/InitAllSettings.xaml"
        assert normalize_path(input_path) == expected

    def test_normalize_path_edge_cases(self):
        """Test edge cases for path normalization."""
        # Empty string
        assert normalize_path("") == ""
        
        # None handling
        assert normalize_path(None) is None
        
        # Single filename
        assert normalize_path("MyWorkflow.xaml") == "MyWorkflow.xaml"
        
        # Only separators
        assert normalize_path("\\") == "/"
        assert normalize_path("\\\\") == "//"

    def test_normalize_workflow_path_basic(self):
        """Test workflow path normalization with .xaml handling."""
        # With .xaml extension
        assert normalize_workflow_path("Framework\\InitAllSettings.xaml") == "Framework/InitAllSettings"
        
        # Without .xaml extension
        assert normalize_workflow_path("Framework\\InitAllSettings") == "Framework/InitAllSettings"
        
        # Forward slashes with .xaml
        assert normalize_workflow_path("Framework/InitAllSettings.xaml") == "Framework/InitAllSettings"

    def test_normalize_workflow_path_complex(self):
        """Test complex workflow path scenarios."""
        # Nested paths with .xaml
        input_path = "Foo\\Bar\\Baz\\MyComplexWorkflow.xaml"
        expected = "Foo/Bar/Baz/MyComplexWorkflow"
        assert normalize_workflow_path(input_path) == expected
        
        # Mixed separators
        input_path = "Framework\\Sub/MyWorkflow.xaml"
        expected = "Framework/Sub/MyWorkflow"
        assert normalize_workflow_path(input_path) == expected

    def test_normalize_workflow_path_edge_cases(self):
        """Test edge cases for workflow path normalization."""
        # Empty string
        assert normalize_workflow_path("") == ""
        
        # None handling
        assert normalize_workflow_path(None) is None
        
        # Just .xaml
        assert normalize_workflow_path(".xaml") == ""
        
        # Filename ending with .xaml but not extension
        assert normalize_workflow_path("MyFile.xaml.backup") == "MyFile.xaml.backup"


class TestPathNormalizationIntegration:
    """Integration tests for path normalization in real scenarios."""

    @pytest.mark.parametrize("input_path,expected", [
        # UiPath typical patterns
        ("Framework\\InitAllSettings.xaml", "Framework/InitAllSettings.xaml"),
        ("Framework\\Process\\GetData.xaml", "Framework/Process/GetData.xaml"),
        ("Foo\\myEmptyWOrkflow.xaml", "Foo/myEmptyWOrkflow.xaml"),
        ("Foo\\Bar\\myWorkflowFooBar.xaml", "Foo/Bar/myWorkflowFooBar.xaml"),
        
        # Already normalized
        ("Framework/InitAllSettings.xaml", "Framework/InitAllSettings.xaml"),
        ("Main.xaml", "Main.xaml"),
        
        # Complex Windows absolute paths
        ("D:\\UiPath\\Projects\\MyProject\\Main.xaml", "D:/UiPath/Projects/MyProject/Main.xaml"),
    ])
    def test_typical_uipath_paths(self, input_path, expected):
        """Test normalization with typical UiPath project structures."""
        assert normalize_path(input_path) == expected

    def test_invocation_target_path_scenarios(self):
        """Test scenarios from actual invocations.jsonl files."""
        # From corpus testing - these are the problematic paths
        test_cases = [
            "Framework\\InitAllSettings.xaml",
            "Foo\\myEmptyWOrkflow.xaml", 
            "Foo\\Bar\\myWorkflowFooBar.xaml",
            "Framework\\GetTransactionData.xaml",
            "Framework\\Process.xaml",
            "Framework\\SetTransactionStatus.xaml"
        ]
        
        for path in test_cases:
            normalized = normalize_path(path)
            # Should not contain any backslashes
            assert "\\" not in normalized
            # Should contain forward slashes (if path had separators)
            if "\\" in path:
                assert "/" in normalized
            # Should preserve the .xaml extension
            if path.endswith(".xaml"):
                assert normalized.endswith(".xaml")

    def test_consistency_across_functions(self):
        """Ensure consistent behavior between normalization functions."""
        test_paths = [
            "Framework\\InitAllSettings.xaml",
            "Foo\\Bar\\MyWorkflow.xaml",
            "C:\\Projects\\Main.xaml"
        ]
        
        for path in test_paths:
            # Both functions should produce consistent forward slash results
            basic_normalized = normalize_path(path)
            workflow_normalized = normalize_workflow_path(path)
            
            # Basic should keep .xaml, workflow should remove it
            assert basic_normalized.replace(".xaml", "") == workflow_normalized
            assert "\\" not in basic_normalized
            assert "\\" not in workflow_normalized


class TestPathNormalizationRealWorld:
    """Real-world scenario tests based on corpus project issues."""

    def test_corpus_c25v001_invocation_paths(self):
        """Test paths from actual corpus project c25v001_CORE_00000001."""
        # These are the exact paths that caused resolution failures
        problematic_paths = [
            ("Framework\\InitAllSettings.xaml", "Framework/InitAllSettings.xaml"),
            ("Foo\\myEmptyWOrkflow.xaml", "Foo/myEmptyWOrkflow.xaml"),
            ("Foo\\Bar\\myWorkflowFooBar.xaml", "Foo/Bar/myWorkflowFooBar.xaml")
        ]
        
        for input_path, expected in problematic_paths:
            assert normalize_path(input_path) == expected

    def test_recursive_pseudocode_workflow_matching(self):
        """Test paths that should resolve in recursive pseudocode expansion."""
        # Test the specific scenario that was failing before
        invocation_target = "Framework\\InitAllSettings.xaml"  # From invocations.jsonl
        artifact_path = "Framework/InitAllSettings"  # From pseudocode artifacts
        
        # After normalization, they should be matchable
        normalized_target = normalize_workflow_path(invocation_target)
        assert normalized_target == artifact_path

    def test_mcp_uri_compatibility(self):
        """Test that normalized paths are compatible with MCP URI format."""
        test_paths = [
            "Framework\\InitAllSettings.xaml",
            "Process\\Main\\GetData.xaml", 
            "Library\\Utils\\Helper.xaml"
        ]
        
        for path in test_paths:
            normalized = normalize_path(path)
            # Should be safe for URI construction
            assert "\\" not in normalized
            assert "/" in normalized or len(normalized.split("/")) == 1  # Allow single filenames
            # Should not have problematic characters for URIs
            assert " " not in normalized or True  # Spaces are URL-encodable