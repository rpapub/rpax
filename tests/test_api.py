"""Tests for rpax Access API implementation."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from rpax.api import ApiError, RpaxApiServer, start_api_server
from rpax.config import ApiConfig, RpaxConfig


class TestApiConfig:
    """Tests for API configuration model."""

    def test_api_config_defaults(self):
        """Test API config default values."""
        config = ApiConfig()
        assert config.enabled is False
        assert config.bind == "127.0.0.1"
        assert config.port == 8623
        assert config.read_only is True

    def test_api_config_validation_bind_address(self):
        """Test bind address validation."""
        # Valid addresses
        valid_addresses = ["127.0.0.1", "localhost", "::1"]
        for addr in valid_addresses:
            config = ApiConfig(bind=addr)
            assert config.bind == addr

        # Invalid addresses
        invalid_addresses = ["0.0.0.0", "192.168.1.1", "example.com"]
        for addr in invalid_addresses:
            with pytest.raises(ValueError, match="bind address must be localhost only"):
                ApiConfig(bind=addr)

    def test_api_config_validation_port_range(self):
        """Test port range validation."""
        # Valid ports
        valid_ports = [1024, 8623, 65535]
        for port in valid_ports:
            config = ApiConfig(port=port)
            assert config.port == port

        # Invalid ports
        invalid_ports = [80, 1023, 65536, 99999]
        for port in invalid_ports:
            with pytest.raises(ValueError, match="port must be between 1024-65535"):
                ApiConfig(port=port)

    def test_api_config_alias_support(self):
        """Test camelCase alias support."""
        config = ApiConfig(readOnly=False)
        assert config.read_only is False


class TestApiServer:
    """Tests for API server functionality."""

    @pytest.fixture
    def temp_lake_dir(self):
        """Create temporary lake directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lake_path = Path(temp_dir) / ".rpax-lake"
            lake_path.mkdir()
            
            # Create basic lake structure
            projects_data = {
                "schemaVersion": "1.0.0",
                "generatedAt": "2025-09-06T10:30:00Z",
                "projects": [
                    {"slug": "test-project-abcd1234", "name": "TestProject"}
                ]
            }
            
            with open(lake_path / "projects.json", 'w') as f:
                json.dump(projects_data, f)
                
            yield lake_path

    @pytest.fixture
    def api_config(self, temp_lake_dir):
        """Create API configuration for testing."""
        from rpax.config import ProjectConfig, OutputConfig, ProjectType
        
        project_config = ProjectConfig(name="TestProject", type=ProjectType.PROCESS)
        output_config = OutputConfig(dir=str(temp_lake_dir))
        api_config = ApiConfig(enabled=True, port=9999)  # Use high port for testing
        
        return RpaxConfig(
            project=project_config,
            output=output_config,
            api=api_config
        )

    def test_server_initialization(self, api_config):
        """Test server initialization."""
        server = RpaxApiServer(api_config)
        assert server.config == api_config
        assert server.server is None
        assert server.actual_port is None

    def test_lake_status_empty(self, api_config):
        """Test lake status with no projects."""
        # Remove projects.json to simulate empty lake
        projects_file = Path(api_config.output.dir) / "projects.json"
        projects_file.unlink()
        
        server = RpaxApiServer(api_config)
        lake_status = server.get_lake_status()
        
        assert len(lake_status) == 1
        assert lake_status[0]["projectCount"] == 0

    def test_lake_status_with_projects(self, api_config):
        """Test lake status with projects."""
        server = RpaxApiServer(api_config)
        lake_status = server.get_lake_status()
        
        assert len(lake_status) == 1
        assert lake_status[0]["projectCount"] == 1
        assert "path" in lake_status[0]
        assert "lastScanAt" in lake_status[0]

    def test_total_project_count(self, api_config):
        """Test total project count calculation."""
        server = RpaxApiServer(api_config)
        total_count = server.get_total_project_count()
        assert total_count == 1

    def test_find_available_port(self, api_config):
        """Test port discovery."""
        server = RpaxApiServer(api_config)
        
        # Should find port >= 1024 (since we set port=0 which gets clamped)
        available_port = server._find_available_port(8623)
        assert 8623 <= available_port <= 65535

    def test_api_disabled_error(self, api_config):
        """Test error when API is disabled."""
        api_config.api.enabled = False
        
        with pytest.raises(ApiError) as exc_info:
            start_api_server(api_config)
        
        assert exc_info.value.status_code == 503
        assert "disabled" in exc_info.value.detail

    @patch('os.environ.get')
    def test_service_discovery_no_localappdata(self, mock_environ, api_config):
        """Test service discovery when LOCALAPPDATA is missing."""
        mock_environ.return_value = None
        
        server = RpaxApiServer(api_config)
        # Should not raise error, just log warning
        server._write_service_info("http://127.0.0.1:8623")

    def test_service_discovery_file_creation(self, api_config):
        """Test service discovery file creation."""
        server = RpaxApiServer(api_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {'LOCALAPPDATA': temp_dir}):
                server._write_service_info("http://127.0.0.1:8623")
                
                service_file = Path(temp_dir) / "rpax" / "api-info.json"
                assert service_file.exists()
                
                with open(service_file) as f:
                    service_data = json.load(f)
                
                assert service_data["url"] == "http://127.0.0.1:8623"
                assert "pid" in service_data
                assert "rpaxVersion" in service_data
                assert len(service_data["lakes"]) == 1

    def test_service_discovery_cleanup(self, api_config):
        """Test service discovery file cleanup."""
        server = RpaxApiServer(api_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            service_file = Path(temp_dir) / "api-info.json"
            service_file.write_text("test")
            
            server.service_info_file = service_file
            server._cleanup_service_info()
            
            assert not service_file.exists()


@pytest.mark.integration 
class TestApiEndpoints:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def running_server(self, temp_lake_dir):
        """Start API server for integration tests."""
        from rpax.config import ProjectConfig, OutputConfig, ProjectType
        
        project_config = ProjectConfig(name="TestProject", type=ProjectType.PROCESS)
        output_config = OutputConfig(dir=str(temp_lake_dir))
        api_config = ApiConfig(enabled=True, port=9998)  # Test port for running server
        
        config = RpaxConfig(
            project=project_config,
            output=output_config,
            api=api_config
        )
        
        server = start_api_server(config)
        yield server
        server.stop()

    @pytest.fixture
    def temp_lake_dir(self):
        """Create temporary lake directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lake_path = Path(temp_dir) / ".rpax-lake" 
            lake_path.mkdir()
            
            # Create basic lake structure
            projects_data = {
                "schemaVersion": "1.0.0",
                "generatedAt": "2025-09-06T10:30:00Z", 
                "projects": [
                    {"slug": "test-project-abcd1234", "name": "TestProject"}
                ]
            }
            
            with open(lake_path / "projects.json", 'w') as f:
                json.dump(projects_data, f)
                
            yield lake_path

    def test_health_endpoint(self, running_server):
        """Test /health endpoint."""
        base_url = f"http://127.0.0.1:{running_server.actual_port}"
        
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_status_endpoint(self, running_server):
        """Test /status endpoint."""
        base_url = f"http://127.0.0.1:{running_server.actual_port}"
        
        response = requests.get(f"{base_url}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "rpaxVersion" in data
        assert "uptime" in data
        assert "startedAt" in data
        assert "mountedLakes" in data
        assert "totalProjectCount" in data
        assert "memoryUsage" in data
        
        # Check lake info
        assert len(data["mountedLakes"]) >= 1
        assert data["totalProjectCount"] >= 1

    def test_unknown_endpoint_404(self, running_server):
        """Test unknown endpoint returns 404."""
        base_url = f"http://127.0.0.1:{running_server.actual_port}"
        
        response = requests.get(f"{base_url}/unknown")
        assert response.status_code == 404
        
        data = response.json()
        assert data["error"] == "not_found"
        assert "traceId" in data
        assert "timestamp" in data

    def test_method_not_allowed(self, running_server):
        """Test POST to GET-only endpoint."""
        base_url = f"http://127.0.0.1:{running_server.actual_port}"
        
        response = requests.post(f"{base_url}/health")
        assert response.status_code == 405


class TestApiError:
    """Tests for API error handling."""

    def test_api_error_creation(self):
        """Test API error creation."""
        error = ApiError(404, "not_found", "Resource not found")
        assert error.status_code == 404
        assert error.error_type == "not_found" 
        assert error.detail == "Resource not found"
        assert str(error) == "not_found: Resource not found"

    def test_api_error_inheritance(self):
        """Test API error inheritance."""
        error = ApiError(500, "internal", "Server error")
        assert isinstance(error, Exception)