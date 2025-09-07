"""Tests for Object Repository parser."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from rpax.parser.object_repository import (
    ObjectRepositoryParser, 
    ObjectRepository, 
    ObjectApp, 
    UITarget, 
    UISelector
)


class TestObjectRepositoryParser:
    """Test Object Repository parsing functionality."""

    def setup_method(self):
        """Set up test parser."""
        self.parser = ObjectRepositoryParser()

    def test_parse_selector_properties(self):
        """Test parsing selector properties from XML string."""
        selector_xml = "&lt;uia automationid='NavView' /&gt;&lt;uia automationid='Header' cls='TextBlock' name='Standard' role='text' /&gt;"
        
        properties = self.parser._parse_selector_properties(selector_xml)
        
        assert "automationid" in properties
        assert "cls" in properties
        assert properties["cls"] == "TextBlock"
        assert properties["name"] == "Standard"
        assert properties["role"] == "text"

    def test_parse_selector_properties_with_app_info(self):
        """Test parsing app information from selectors."""
        selector_xml = "&lt;wnd app='applicationframehost.exe' appid='Microsoft.WindowsCalculator_8wekyb3d8bbwe!App' /&gt;"
        
        properties = self.parser._parse_selector_properties(selector_xml)
        
        assert properties["app"] == "applicationframehost.exe"
        assert properties["appid"] == "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"

    def test_parse_empty_selector_properties(self):
        """Test parsing empty or None selector."""
        assert self.parser._parse_selector_properties("") == {}
        assert self.parser._parse_selector_properties(None) == {}

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_parse_repository_nonexistent_path(self, mock_is_dir, mock_exists):
        """Test parsing with nonexistent path."""
        mock_exists.return_value = False
        mock_is_dir.return_value = False
        
        result = self.parser.parse_repository(Path("/nonexistent"))
        
        assert result is None

    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.iterdir')
    def test_parse_library_metadata_with_bom(self, mock_iterdir, mock_is_dir, mock_exists, mock_open):
        """Test parsing library metadata with BOM."""
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_iterdir.return_value = []
        
        # Mock metadata file with BOM
        metadata_content = '\ufeff{"Type": "Library", "Id": "test-id"}'
        mock_open.return_value.__enter__.return_value.read.return_value = metadata_content
        
        # Mock the metadata file path exists check
        with patch.object(Path, 'exists', return_value=True):
            result = self.parser.parse_repository(Path("/test/.objects"))
        
        assert result is not None
        assert result.library_type == "Library"
        assert result.library_id == "test-id"

    def test_generate_mcp_resources(self):
        """Test MCP resources generation."""
        # Create test repository
        target = UITarget(
            target_id="test-target",
            friendly_name="Test Button",
            element_type="Button",
            reference="test-ref",
            selectors=[
                UISelector(
                    selector_type="full",
                    selector_value="<button>Test</button>",
                    properties={"name": "Test Button"}
                )
            ]
        )
        
        app = ObjectApp(
            app_id="test-app",
            name="Test Application",
            description="Test app description",
            reference="test-app-ref",
            targets=[target]
        )
        
        repository = ObjectRepository(
            library_id="test-library",
            apps=[app]
        )
        
        resources = self.parser.generate_mcp_resources(repository, "test-project")
        
        # Check library resource
        assert len(resources) == 2  # Library + app resource
        
        library_resource = resources[0]
        assert library_resource["uri"] == "rpax://test-project/object-repository"
        assert library_resource["name"] == "Object Repository Library (test-project)"
        assert library_resource["content"]["apps_count"] == 1
        
        # Check app resource
        app_resource = resources[1]
        assert app_resource["uri"] == "rpax://test-project/object-repository/apps/test-app"
        assert app_resource["name"] == "Object Repository App: Test Application"
        assert len(app_resource["content"]["targets"]) == 1
        
        target_data = app_resource["content"]["targets"][0]
        assert target_data["friendly_name"] == "Test Button"
        assert target_data["element_type"] == "Button"
        assert len(target_data["selectors"]) == 1
        assert target_data["selectors"][0]["type"] == "full"


class TestObjectRepositoryIntegration:
    """Integration tests with real Object Repository structure."""
    
    def test_lucky_lawrencium_structure_detection(self):
        """Test detection of LuckyLawrencium Object Repository structure."""
        lucky_path = Path("D:/github.com/rpapub/LuckyLawrencium/.objects")
        
        if not lucky_path.exists():
            pytest.skip("LuckyLawrencium test project not available")
            
        parser = ObjectRepositoryParser()
        repository = parser.parse_repository(lucky_path)
        
        # Basic structure validation
        assert repository is not None
        assert repository.library_type == "Library"
        assert len(repository.apps) > 0
        
        # Check Calculator app exists
        calculator_app = next((app for app in repository.apps if "Calculator" in app.name), None)
        assert calculator_app is not None
        assert calculator_app.name == "Calculator"
        assert len(calculator_app.targets) > 0
        
        # Check targets have selectors
        for target in calculator_app.targets:
            assert target.target_id is not None
            assert target.friendly_name is not None
            # At least one selector should be present
            assert len(target.selectors) > 0
            
        # Generate MCP resources
        resources = parser.generate_mcp_resources(repository, "luckylawrencium-test")
        assert len(resources) >= 2  # At least library + one app

    def test_mcp_resources_structure(self):
        """Test MCP resources have proper structure."""
        lucky_path = Path("D:/github.com/rpapub/LuckyLawrencium/.objects")
        
        if not lucky_path.exists():
            pytest.skip("LuckyLawrencium test project not available")
            
        parser = ObjectRepositoryParser()
        repository = parser.parse_repository(lucky_path)
        
        resources = parser.generate_mcp_resources(repository, "test-project")
        
        # Validate resource structure
        for resource in resources:
            assert "uri" in resource
            assert "name" in resource
            assert "description" in resource
            assert "mimeType" in resource
            assert "content" in resource
            
            # URI should follow rpax:// scheme
            assert resource["uri"].startswith("rpax://test-project/object-repository")
            assert resource["mimeType"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])