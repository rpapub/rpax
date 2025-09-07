"""Minimal Access API server implementation per ADR-022."""

import json
import logging
import os
import socket
import threading
import time
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rpax import __version__
from rpax.config import RpaxConfig

# Optional psutil import for memory monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """API error with HTTP status code."""

    def __init__(self, status_code: int, error_type: str, detail: str):
        self.status_code = status_code
        self.error_type = error_type
        self.detail = detail
        super().__init__(f"{error_type}: {detail}")


class RpaxApiHandler(BaseHTTPRequestHandler):
    """HTTP request handler for rpax API endpoints."""

    def __init__(self, request, client_address, server, api_server):
        self.api_server = api_server
        super().__init__(request, client_address, server)

    def log_message(self, format, *args):
        """Override to use rpax logger instead of stderr."""
        logger.info(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        """Handle GET requests."""
        start_time = time.time()
        status_code = 500  # Default to error
        
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path

            if path == "/health":
                self._handle_health()
                status_code = 200
            elif path == "/status":
                self._handle_status()
                status_code = 200
            elif path == "/openapi.yaml":
                self._handle_openapi_yaml()
                status_code = 200
            elif path == "/openapi.json":
                self._handle_openapi_json()
                status_code = 200
            elif path == "/docs" or path == "/docs/":
                self._handle_swagger_ui()
                status_code = 200
            elif path == "/favicon.ico":
                self._handle_favicon()
                status_code = 200
            else:
                raise ApiError(404, "not_found", f"Unknown endpoint: {path}")

        except ApiError as e:
            status_code = e.status_code
            self._send_error_response(e)
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            # Client closed connection - ignore silently
            status_code = 0  # Special code for connection errors
            pass
        except Exception as e:
            logger.exception(f"Unexpected error handling {self.path}")
            status_code = 500
            error = ApiError(500, "internal", "Internal server error")
            self._send_error_response(error)
        finally:
            # Access logging (only if verbose mode enabled)
            if self.api_server.verbose and status_code != 0:
                elapsed_ms = int((time.time() - start_time) * 1000)
                client_ip = self.client_address[0]
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] GET {self.path} {status_code} {elapsed_ms}ms {client_ip}")

    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)."""
        try:
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
            self.end_headers()
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            # Client closed connection - ignore silently
            pass

    def do_POST(self):
        """Handle POST requests - not allowed in read-only API."""
        self._send_method_not_allowed()

    def do_PUT(self):
        """Handle PUT requests - not allowed in read-only API."""
        self._send_method_not_allowed()

    def do_DELETE(self):
        """Handle DELETE requests - not allowed in read-only API."""
        self._send_method_not_allowed()

    def do_PATCH(self):
        """Handle PATCH requests - not allowed in read-only API."""
        self._send_method_not_allowed()

    def _send_method_not_allowed(self):
        """Send 405 Method Not Allowed response."""
        error = ApiError(405, "method_not_allowed", "Method not allowed - read-only API")
        self._send_error_response(error)

    def _handle_health(self):
        """Handle /health endpoint."""
        response = {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat()
        }
        self._send_json_response(200, response)

    def _handle_status(self):
        """Handle /status endpoint."""
        uptime_seconds = time.time() - self.api_server.start_time
        uptime_str = self._format_uptime(uptime_seconds)

        # Get memory usage if psutil is available
        if HAS_PSUTIL:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_usage = {
                    "heapUsed": f"{memory_info.rss / 1024 / 1024:.1f}MB",
                    "heapTotal": f"{memory_info.vms / 1024 / 1024:.1f}MB"
                }
            except Exception:
                memory_usage = {"heapUsed": "N/A", "heapTotal": "N/A"}
        else:
            memory_usage = {"heapUsed": "N/A", "heapTotal": "N/A"}

        response = {
            "rpaxVersion": __version__,
            "uptime": uptime_str,
            "startedAt": datetime.fromtimestamp(self.api_server.start_time, UTC).isoformat(),
            "mountedLakes": self.api_server.get_lake_status(),
            "totalProjectCount": self.api_server.get_total_project_count(),
            "latestActivityAt": self.api_server.get_latest_activity(),
            "memoryUsage": memory_usage
        }
        self._send_json_response(200, response)

    def _handle_openapi_yaml(self):
        """Handle /openapi.yaml endpoint."""
        try:
            # Load the generated OpenAPI spec
            openapi_path = Path("docs/api/v0/openapi.yaml")
            if not openapi_path.exists():
                raise ApiError(404, "not_found", "OpenAPI specification not found. Run 'uv run python tools/generate_openapi.py' to generate it.")
            
            with open(openapi_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()
            
            response_bytes = yaml_content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/yaml; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
            
        except Exception as e:
            logger.exception("Error serving OpenAPI YAML")
            raise ApiError(500, "internal", f"Failed to serve OpenAPI specification: {str(e)}")

    def _handle_openapi_json(self):
        """Handle /openapi.json endpoint.""" 
        try:
            # Load the generated OpenAPI spec as JSON
            openapi_path = Path("docs/api/v0/openapi.json")
            if openapi_path.exists():
                with open(openapi_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                self._send_json_response(200, json_data)
            else:
                # Try to load YAML and convert to JSON
                yaml_path = Path("docs/api/v0/openapi.yaml")
                if not yaml_path.exists():
                    raise ApiError(404, "not_found", "OpenAPI specification not found. Run 'uv run python tools/generate_openapi.py' to generate it.")
                
                try:
                    import yaml
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f)
                    self._send_json_response(200, yaml_data)
                except ImportError:
                    raise ApiError(500, "internal", "YAML support not available. Install PyYAML or generate OpenAPI as JSON.")
                    
        except Exception as e:
            logger.exception("Error serving OpenAPI JSON")
            raise ApiError(500, "internal", f"Failed to serve OpenAPI specification: {str(e)}")

    def _handle_swagger_ui(self):
        """Handle /docs endpoint - serve Swagger UI."""
        try:
            swagger_path = Path("docs/api/v0/swagger-ui.html")
            if not swagger_path.exists():
                raise ApiError(404, "not_found", "Swagger UI not found. The swagger-ui.html file should exist at docs/api/v0/")
            
            with open(swagger_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Update the OpenAPI spec URL to point to this server
            html_content = html_content.replace(
                "url: './openapi.yaml'",
                f"url: 'http://localhost:{self.api_server.actual_port}/openapi.yaml'"
            )
            
            response_bytes = html_content.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
            
        except Exception as e:
            logger.exception("Error serving Swagger UI")
            raise ApiError(500, "internal", f"Failed to serve Swagger UI: {str(e)}")

    def _handle_favicon(self):
        """Handle /favicon.ico endpoint - return minimal ICO to prevent 404s."""
        # Minimal valid ICO file (16x16 transparent icon)
        ico_data = bytes.fromhex(
            "00000100010010100000010020006804000016000000280000001000000020000000"
            "0100200000000000400400000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000"
        )
        
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'image/x-icon')
            self.send_header('Content-Length', str(len(ico_data)))
            self.send_header('Cache-Control', 'public, max-age=86400')  # Cache for 24 hours
            self.end_headers()
            self.wfile.write(ico_data)
        except (ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime duration."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h{minutes}m{secs}s"

    def _send_json_response(self, status_code: int, data: Any):
        """Send JSON response."""
        response_json = json.dumps(data, indent=2, ensure_ascii=False)
        response_bytes = response_json.encode('utf-8')

        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(response_bytes)))
            # CORS headers for Swagger UI cross-origin requests
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
            self.end_headers()
            self.wfile.write(response_bytes)
        except (ConnectionAbortedError, BrokenPipeError, OSError) as e:
            # Client closed connection before response was sent - this is normal
            # Silently ignore connection errors to avoid spam in logs
            pass

    def _send_error_response(self, error: ApiError):
        """Send standardized error response."""
        response = {
            "error": error.error_type,
            "detail": error.detail,
            "traceId": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "requestPath": self.path
        }
        self._send_json_response(error.status_code, response)


class RpaxApiServer:
    """Minimal rpax Access API server per ADR-022."""

    def __init__(self, config: RpaxConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.start_time = time.time()
        self.server = None
        self.server_thread = None
        self.actual_port = None
        self.service_info_file = None

    def get_lake_status(self) -> list[dict[str, Any]]:
        """Get status of mounted lakes."""
        lake_path = Path(self.config.output.dir)
        if not lake_path.exists():
            return []

        try:
            project_count = self._count_projects_in_lake(lake_path)
            return [{
                "path": str(lake_path.absolute()),
                "projectCount": project_count,
                "lastScanAt": datetime.now(UTC).isoformat()  # Placeholder - would track actual scan time
            }]
        except Exception:
            logger.exception(f"Error reading lake status from {lake_path}")
            return []

    def _count_projects_in_lake(self, lake_path: Path) -> int:
        """Count projects in lake directory."""
        try:
            projects_file = lake_path / "projects.json"
            if projects_file.exists():
                with open(projects_file) as f:
                    projects_data = json.load(f)
                    return len(projects_data.get("projects", []))
        except Exception:
            pass
        
        # Fallback: count project directories
        project_dirs = [d for d in lake_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        return len(project_dirs)

    def get_total_project_count(self) -> int:
        """Get total project count across all lakes."""
        return sum(lake["projectCount"] for lake in self.get_lake_status())

    def get_latest_activity(self) -> str:
        """Get timestamp of latest activity."""
        return datetime.fromtimestamp(self.start_time, UTC).isoformat()

    def _find_available_port(self, start_port: int) -> int:
        """Find available port starting from start_port."""
        max_attempts = 100
        for port in range(start_port, start_port + max_attempts):
            try:
                # Test if port is available
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.config.api.bind, port))
                    return port
            except OSError:
                continue
        
        raise ApiError(503, "service_unavailable", f"No available ports found starting from {start_port}")

    def _write_service_info(self, url: str):
        """Write service discovery file per ADR-022."""
        try:
            # Get LOCALAPPDATA directory
            local_app_data = os.environ.get('LOCALAPPDATA')
            if not local_app_data:
                logger.warning("LOCALAPPDATA not found, skipping service discovery file")
                return

            rpax_dir = Path(local_app_data) / "rpax"
            rpax_dir.mkdir(exist_ok=True)
            
            service_info = {
                "url": url,
                "pid": os.getpid(),
                "startedAt": datetime.fromtimestamp(self.start_time, UTC).isoformat(),
                "rpaxVersion": __version__,
                "lakes": [str(Path(self.config.output.dir).absolute())],
                "projectCount": self.get_total_project_count(),
                "configPath": ""  # Would be populated if config file path is tracked
            }

            self.service_info_file = rpax_dir / "api-info.json"
            
            # Atomic write with temp file + rename
            temp_file = self.service_info_file.with_suffix(".tmp")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(service_info, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.service_info_file)
            logger.info(f"Service discovery file written: {self.service_info_file}")

        except Exception:
            logger.exception("Failed to write service discovery file")

    def _cleanup_service_info(self):
        """Cleanup service discovery file on shutdown."""
        if self.service_info_file and self.service_info_file.exists():
            try:
                self.service_info_file.unlink()
                logger.info("Service discovery file cleaned up")
            except Exception:
                logger.exception("Failed to cleanup service discovery file")

    def start(self) -> str:
        """Start the API server."""
        if not self.config.api.enabled:
            raise ApiError(503, "service_unavailable", "API is disabled in configuration")

        # Find available port
        self.actual_port = self._find_available_port(self.config.api.port)
        
        # Create server
        def handler_factory(request, client_address, server):
            return RpaxApiHandler(request, client_address, server, self)

        self.server = ThreadingHTTPServer((self.config.api.bind, self.actual_port), handler_factory)
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        # Construct URL and write service discovery
        url = f"http://{self.config.api.bind}:{self.actual_port}"
        self._write_service_info(url)

        # Single-line startup output per ADR-022
        project_count = self.get_total_project_count()
        lake_count = len(self.get_lake_status())
        lake_suffix = "s" if lake_count != 1 else ""
        startup_message = f"rpax API started at {url} ({project_count} projects, {lake_count} lake{lake_suffix})"
        print(startup_message)
        logger.info(startup_message)

        return url

    def stop(self):
        """Stop the API server."""
        if self.server:
            logger.info("Shutting down API server...")
            self.server.shutdown()
            self.server.server_close()
            
            if self.server_thread:
                self.server_thread.join(timeout=5.0)
            
            self._cleanup_service_info()
            logger.info("API server stopped")


def start_api_server(config: RpaxConfig, verbose: bool = False) -> RpaxApiServer:
    """Start rpax API server with given configuration."""
    server = RpaxApiServer(config, verbose=verbose)
    server.start()
    return server