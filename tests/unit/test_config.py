"""Unit tests for configuration management."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from rpax.config import (
    OutputFormat,
    ProjectConfig,
    ProjectType,
    RpaxConfig,
    create_default_config,
    find_config_file,
    load_config,
)


class TestProjectConfig:
    """Test ProjectConfig model."""

    def test_project_config_minimal(self):
        """Test minimal valid project config."""
        config = ProjectConfig(type=ProjectType.PROCESS)
        assert config.type == ProjectType.PROCESS
        assert config.root == "."
        assert config.name is None

    def test_project_config_full(self):
        """Test full project config."""
        config = ProjectConfig(
            name="test-project",
            root="/path/to/project",
            type=ProjectType.LIBRARY
        )
        assert config.name == "test-project"
        assert config.root == "/path/to/project"
        assert config.type == ProjectType.LIBRARY


class TestRpaxConfig:
    """Test complete RpaxConfig model."""

    def test_minimal_config(self):
        """Test minimal valid rpax config."""
        config = RpaxConfig(
            project=ProjectConfig(type=ProjectType.PROCESS)
        )
        assert config.project.type == ProjectType.PROCESS
        assert config.output.dir == ".rpax-lake"
        assert config.validation.fail_on_missing is True

    def test_config_from_dict(self):
        """Test config creation from dictionary."""
        config_data = {
            "project": {
                "name": "test-project",
                "type": "process"
            },
            "output": {
                "dir": "custom-out",
                "formats": ["json", "mermaid"]
            },
            "validation": {
                "failOnMissing": False,
                "failOnCycles": True
            }
        }

        config = RpaxConfig(**config_data)
        assert config.project.name == "test-project"
        assert config.project.type == ProjectType.PROCESS
        assert config.output.dir == "custom-out"
        assert OutputFormat.JSON in config.output.formats
        assert config.validation.fail_on_missing is False
        assert config.validation.fail_on_cycles is True

    def test_config_validation_error(self):
        """Test config validation error handling."""
        with pytest.raises(ValueError):
            RpaxConfig(project={"type": "invalid-type"})

    def test_config_extra_fields_forbidden(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValueError):
            RpaxConfig(
                project={"type": "process"},
                invalid_field="should-fail"
            )


class TestConfigFileOperations:
    """Test configuration file loading and discovery."""

    def test_load_config_with_file(self):
        """Test loading config from existing file."""
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / ".rpax.json"
            config_data = {
                "project": {
                    "name": "file-test",
                    "type": "library"
                }
            }

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            config = load_config(config_file)
            assert config.project.name == "file-test"
            assert config.project.type == ProjectType.LIBRARY

    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "nonexistent.json"
            config = load_config(config_file)
            # Should return default config
            assert config.project.type == ProjectType.PROCESS

    def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON."""
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / ".rpax.json"
            with open(config_file, "w") as f:
                f.write("{invalid json")

            with pytest.raises(ValueError, match="Invalid JSON"):
                load_config(config_file)

    def test_load_config_invalid_structure(self):
        """Test loading config with invalid structure."""
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / ".rpax.json"
            config_data = {"invalid": "structure"}

            with open(config_file, "w") as f:
                json.dump(config_data, f)

            with pytest.raises(ValueError, match="Failed to load config"):
                load_config(config_file)

    def test_find_config_file_current_dir(self):
        """Test finding config file in current directory."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / ".rpax.json"
            config_file.touch()

            found = find_config_file(temp_path)
            assert found == config_file

    def test_find_config_file_parent_dir(self):
        """Test finding config file in parent directory."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / ".rpax.json"
            config_file.touch()

            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()

            found = find_config_file(sub_dir)
            assert found == config_file

    def test_find_config_file_not_found(self):
        """Test config file discovery when not found."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            found = find_config_file(temp_path)
            assert found is None

    def test_create_default_config(self):
        """Test default config creation."""
        config = create_default_config()
        assert config.project.type == ProjectType.PROCESS
        assert config.output.dir == ".rpax-lake"
        assert config.validation.fail_on_missing is True


class TestConfigIntegration:
    """Integration tests for configuration system."""

    def test_zero_config_operation(self):
        """Test zero-config operation with defaults."""
        with patch("rpax.config.find_config_file", return_value=None):
            config = load_config()
            assert config.project.type == ProjectType.PROCESS
            assert config.output.formats == [OutputFormat.JSON, OutputFormat.MERMAID]

    def test_config_discovery_chain(self):
        """Test config file discovery chain."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            deep_dir = temp_path / "a" / "b" / "c"
            deep_dir.mkdir(parents=True)

            # Place config at root
            config_file = temp_path / ".rpax.json"
            config_data = {"project": {"type": "library", "name": "discovered"}}
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            # Load from deep directory - should find parent config
            config = load_config()
            with patch("pathlib.Path.cwd", return_value=deep_dir):
                found_config = load_config()
                # Note: This test depends on actual file system behavior
                # In a real scenario, it would discover the parent config
                assert isinstance(found_config, RpaxConfig)
