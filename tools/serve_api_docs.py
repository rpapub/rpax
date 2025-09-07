#!/usr/bin/env python3
"""Simple HTTP server to serve OpenAPI documentation with Swagger UI.

Usage:
    python tools/serve_api_docs.py [--port 8080] [--api-version v0]
    
    Then visit: http://localhost:8080/swagger-ui.html
"""

import argparse
import http.server
import socketserver
import os
import webbrowser
from pathlib import Path


def serve_api_docs(port: int = 8080, api_version: str = "v0", auto_open: bool = True):
    """Serve OpenAPI documentation with Swagger UI."""
    
    # Change to the API docs directory
    docs_dir = Path(f"docs/api/{api_version}")
    if not docs_dir.exists():
        print(f"Error: API documentation directory not found: {docs_dir}")
        print("Run 'python tools/generate_openapi.py' first to generate the OpenAPI spec.")
        return 1
    
    os.chdir(docs_dir)
    
    # Check if openapi.yaml exists
    if not Path("openapi.yaml").exists():
        print(f"Error: openapi.yaml not found in {docs_dir}")
        print("Run 'python tools/generate_openapi.py' first to generate the OpenAPI spec.")
        return 1
    
    # Check if swagger-ui.html exists
    if not Path("swagger-ui.html").exists():
        print(f"Error: swagger-ui.html not found in {docs_dir}")
        print("The Swagger UI HTML file should be generated automatically.")
        return 1
    
    # Start the HTTP server
    handler = http.server.SimpleHTTPRequestHandler
    
    # Add CORS headers to allow local access
    class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
    
    try:
        with socketserver.TCPServer(("", port), CORSRequestHandler) as httpd:
            swagger_url = f"http://localhost:{port}/swagger-ui.html"
            openapi_url = f"http://localhost:{port}/openapi.yaml"
            
            print(f"Serving OpenAPI documentation on port {port}")
            print(f"Swagger UI: {swagger_url}")
            print(f"OpenAPI spec: {openapi_url}")
            print(f"Serving from: {Path.cwd()}")
            print()
            print("Press Ctrl+C to stop the server")
            
            if auto_open:
                try:
                    webbrowser.open(swagger_url)
                    print(f"Opening {swagger_url} in your default browser...")
                except Exception as e:
                    print(f"Could not auto-open browser: {e}")
            
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"Error: Port {port} is already in use. Try a different port with --port")
            return 1
        else:
            print(f"Error starting server: {e}")
            return 1
    except KeyboardInterrupt:
        print("\nServer stopped")
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Serve OpenAPI documentation with Swagger UI")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080)")
    parser.add_argument("--api-version", default="v0", help="API version to serve (default: v0)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    
    args = parser.parse_args()
    
    return serve_api_docs(
        port=args.port,
        api_version=args.api_version,
        auto_open=not args.no_open
    )


if __name__ == "__main__":
    exit(main())