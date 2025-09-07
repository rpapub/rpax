"""Tests for rock-solid project slug sanitization."""

import pytest
from rpax.models.project import UiPathProject


class TestSlugSanitization:
    """Test comprehensive slug sanitization for CLI and MCP URI safety."""

    def test_sanitize_basic_names(self):
        """Test basic name sanitization."""
        project = UiPathProject(
            name="My Project",
            project_id="test-id",
            main="Main.xaml",
            uipath_schema_version="1.0"
        )
        
        result = project._sanitize_slug_name("My Project")
        assert result == "my-project"
        
        result = project._sanitize_slug_name("Calculator-Tool")
        assert result == "calculator-tool"
        
        result = project._sanitize_slug_name("simple")
        assert result == "simple"

    def test_sanitize_comma_safety(self):
        """Test comma removal for CLI safety."""
        project = UiPathProject(
            name="Test",
            project_id="test-id", 
            main="Main.xaml",
            uipath_schema_version="1.0"
        )
        
        # Commas should be converted to hyphens
        result = project._sanitize_slug_name("Project,Name,With,Commas")
        assert result == "project-name-with-commas"
        
        # Edge case: only commas
        result = project._sanitize_slug_name(",,")
        assert result == ""

    def test_sanitize_mcp_uri_safety(self):
        """Test URI-unsafe characters removal."""
        project = UiPathProject(
            name="Test",
            project_id="test-id",
            main="Main.xaml", 
            uipath_schema_version="1.0"
        )
        
        # Special characters that are not URI-safe
        result = project._sanitize_slug_name("Project@#$%Name")
        assert result == "project-name"
        
        # Unicode characters
        result = project._sanitize_slug_name("Prøject Näme")
        assert result == "pr-ject-n-me"
        
        # Spaces and tabs
        result = project._sanitize_slug_name("Project\t\nName")
        assert result == "project-name"

    def test_sanitize_consecutive_hyphens(self):
        """Test consecutive hyphen collapsing."""
        project = UiPathProject(
            name="Test",
            project_id="test-id",
            main="Main.xaml",
            uipath_schema_version="1.0"
        )
        
        # Multiple hyphens should collapse to single
        result = project._sanitize_slug_name("My--Project---Name")
        assert result == "my-project-name"
        
        # Mixed special chars creating consecutive hyphens
        result = project._sanitize_slug_name("Project@@@@Name")
        assert result == "project-name"

    def test_sanitize_edge_cases(self):
        """Test edge case sanitization."""
        project = UiPathProject(
            name="Test",
            project_id="test-id",
            main="Main.xaml",
            uipath_schema_version="1.0"
        )
        
        # Leading/trailing hyphens should be stripped
        result = project._sanitize_slug_name("-Project-")
        assert result == "project"
        
        # Empty or whitespace-only should return empty
        result = project._sanitize_slug_name("")
        assert result == ""
        
        result = project._sanitize_slug_name("   ")
        assert result == ""
        
        result = project._sanitize_slug_name(None)
        assert result == ""
        
        # Only special characters should return empty
        result = project._sanitize_slug_name("@#$%^&*()")
        assert result == ""

    def test_generate_slug_with_sanitization(self):
        """Test full slug generation with sanitization."""
        # Test with problematic project name
        project = UiPathProject(
            name="My,Complex@Project!!!",
            project_id="test-id",
            main="Main.xaml",
            uipath_schema_version="1.0"
        )
        
        slug = project.generate_project_slug()
        
        # Should start with sanitized name
        assert slug.startswith("my-complex-project-")
        
        # Should end with 10-character hash
        parts = slug.split("-")
        hash_part = parts[-1]
        assert len(hash_part) == 10
        assert hash_part.isalnum()
        
        # Should contain no commas or special characters
        assert "," not in slug
        assert "@" not in slug
        assert "!" not in slug

    def test_empty_name_fallback(self):
        """Test fallback to 'unnamed' for empty sanitized names.""" 
        project = UiPathProject(
            name="@#$%",  # Only special chars
            project_id="test-id",
            main="Main.xaml", 
            uipath_schema_version="1.0"
        )
        
        slug = project.generate_project_slug()
        
        # Should use 'unnamed' fallback
        assert slug.startswith("unnamed-")
        
        # Should still have hash
        parts = slug.split("-")
        assert len(parts) == 2
        assert len(parts[1]) == 10

    def test_real_world_project_names(self):
        """Test sanitization with real-world UiPath project names."""
        project = UiPathProject(
            name="Test",
            project_id="test-id", 
            main="Main.xaml",
            uipath_schema_version="1.0"
        )
        
        test_cases = [
            ("CPRIMA-USG-001_ShouldStopPresence", "cprima-usg-001-shouldstoppresence"),
            ("Invoice Processing v2.1", "invoice-processing-v2-1"),
            ("Customer Portal (Beta)", "customer-portal-beta"),
            ("Data Migration & Cleanup", "data-migration-cleanup"),
            ("Process/Workflow Template", "process-workflow-template"),
            ("Test-Project_Final.Version", "test-project-final-version"),
        ]
        
        for input_name, expected in test_cases:
            result = project._sanitize_slug_name(input_name)
            assert result == expected, f"Failed for {input_name}: got {result}, expected {expected}"