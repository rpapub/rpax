#!/usr/bin/env python3
"""Generate OpenAPI specification from decorated CLI commands.

This tool extracts API metadata from @api_expose() decorators and combines it
with CLI parameter information to generate a complete OpenAPI 3.0 specification.

Usage:
    python tools/generate_openapi.py
    
Output:
    docs/openapi.yaml - Complete OpenAPI 3.0 specification
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    yaml = None


def load_cli_reference() -> Dict[str, Any]:
    """Load the CLI reference JSON with complete command structure."""
    cli_ref_path = Path("docs/cli-reference.json")
    if not cli_ref_path.exists():
        raise FileNotFoundError(f"CLI reference not found: {cli_ref_path}")
    
    with open(cli_ref_path) as f:
        return json.load(f)


def extract_decorator_metadata() -> Dict[str, Dict[str, Any]]:
    """Extract @api_expose() metadata from decorated CLI commands.
    
    Dynamically imports the CLI module and inspects all functions
    for @api_expose() decorator metadata.
    """
    import importlib.util
    import inspect
    
    # Add src directory to path for importing
    src_path = Path("src")
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    try:
        # Import the CLI module
        from rpax.cli import app
        
        metadata = {}
        
        # Get all registered commands from the Typer app
        for command_info in app.registered_commands.values():
            func = command_info.callback
            
            # Check if function has API metadata
            if hasattr(func, '_rpax_api'):
                api_meta = func._rpax_api
                
                # Only include enabled commands
                if api_meta.get('enabled', True):
                    func_name = func.__name__
                    metadata[func_name] = api_meta.copy()
        
        # Also check registered groups/subcommands
        for group_info in app.registered_groups.values():
            if hasattr(group_info, 'typer_instance'):
                subapp = group_info.typer_instance
                for subcommand_info in subapp.registered_commands.values():
                    func = subcommand_info.callback
                    
                    if hasattr(func, '_rpax_api'):
                        api_meta = func._rpax_api
                        
                        if api_meta.get('enabled', True):
                            func_name = func.__name__
                            metadata[func_name] = api_meta.copy()
        
        print(f"Extracted metadata from {len(metadata)} decorated functions")
        return metadata
        
    except ImportError as e:
        print(f"Warning: Could not import CLI module: {e}")
        print("Falling back to static metadata extraction...")
        
        # Fallback to parsing the CLI source file directly
        return extract_metadata_from_source()
    
    except Exception as e:
        print(f"Error extracting decorator metadata: {e}")
        print("Falling back to static metadata extraction...")
        return extract_metadata_from_source()


def extract_metadata_from_source() -> Dict[str, Dict[str, Any]]:
    """Fallback: Parse CLI source file directly for @api_expose() decorators."""
    import ast
    import re
    
    cli_path = Path("src/rpax/cli.py")
    if not cli_path.exists():
        raise FileNotFoundError(f"CLI source not found: {cli_path}")
    
    metadata = {}
    
    with open(cli_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    # Use regex to find @api_expose decorators and their associated functions
    # This is a simplified approach - in production, you'd want more robust AST parsing
    decorator_pattern = r'@api_expose\((.*?)\)\s*def\s+(\w+)'
    
    for match in re.finditer(decorator_pattern, source, re.DOTALL):
        decorator_args = match.group(1)
        func_name = match.group(2)
        
        # Parse decorator arguments (simplified)
        api_meta = {
            'enabled': True,
            'methods': ['GET'],
            'tags': [],
            'mcp_hints': {}
        }
        
        # Extract basic parameters using regex (not a complete parser)
        if 'enabled=False' in decorator_args:
            api_meta['enabled'] = False
        
        if 'path=' in decorator_args:
            path_match = re.search(r'path=[\'"](.*?)[\'"]', decorator_args)
            if path_match:
                api_meta['path'] = path_match.group(1)
        
        if 'methods=' in decorator_args:
            methods_match = re.search(r'methods=\[(.*?)\]', decorator_args)
            if methods_match:
                methods_str = methods_match.group(1)
                api_meta['methods'] = [m.strip('"\'') for m in methods_str.split(',')]
        
        if 'summary=' in decorator_args:
            summary_match = re.search(r'summary=[\'"](.*?)[\'"]', decorator_args)
            if summary_match:
                api_meta['summary'] = summary_match.group(1)
        
        if 'tags=' in decorator_args:
            tags_match = re.search(r'tags=\[(.*?)\]', decorator_args)
            if tags_match:
                tags_str = tags_match.group(1)
                api_meta['tags'] = [t.strip('"\'') for t in tags_str.split(',')]
        
        # Only include enabled commands
        if api_meta['enabled']:
            metadata[func_name] = api_meta
    
    print(f"Extracted metadata from {len(metadata)} functions via source parsing")
    return metadata


def map_typer_type_to_openapi(param_type: str) -> Dict[str, Any]:
    """Map Typer parameter types to OpenAPI schema types."""
    type_mapping = {
        "STRING": {"type": "string"},
        "INT": {"type": "integer"},
        "BOOL": {"type": "boolean"},
        "PATH": {"type": "string", "format": "path"},
        "FLOAT": {"type": "number"},
    }
    
    # Handle complex types
    if "typer.models.TyperPath" in param_type:
        return {"type": "string", "format": "path"}
    elif "List[" in param_type or "list[" in param_type:
        return {"type": "array", "items": {"type": "string"}}
    
    return type_mapping.get(param_type, {"type": "string"})


def generate_parameter_schema(cli_param: Dict[str, Any], is_path_param: bool = False) -> Dict[str, Any]:
    """Generate OpenAPI parameter schema from CLI parameter info."""
    param = {
        "name": cli_param["name"],
        "in": "path" if is_path_param else ("query" if cli_param.get("is_option") else "query"),
        "required": is_path_param or cli_param.get("required", False),
        "description": cli_param.get("help", ""),
        "schema": map_typer_type_to_openapi(str(cli_param.get("type", "STRING")))
    }
    
    # Add default value if present
    if not is_path_param and cli_param.get("default") is not None:
        param["schema"]["default"] = cli_param["default"]
    
    return param


def extract_path_parameters(api_path: str) -> List[str]:
    """Extract path parameter names from API path template."""
    import re
    return re.findall(r'\{(\w+)\}', api_path)


def generate_openapi_paths(cli_data: Dict[str, Any], decorator_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Generate OpenAPI paths from CLI commands and decorator metadata."""
    paths = {}
    
    # Map CLI command names to their info
    cli_commands = {}
    for cmd in cli_data["command_tree"]["subcommands"]:
        cli_commands[cmd["name"]] = cmd
    
    # Function name to command name mapping
    func_name_to_cmd = {
        "list_items": "list",
        "parse": "parse", 
        "validate": "validate",
        "graph": "graph",
        "explain": "explain",
        "schema": "schema",
        "help": "help",
        "activities": "activities",
        "projects": "projects",
        "clear": "clear",
        "pseudocode": "pseudocode",
        "api": "api",
        "health": "health"
    }
    
    for func_name, api_meta in decorator_metadata.items():
        # Find corresponding CLI command
        cmd_name = func_name_to_cmd.get(func_name, func_name)
        cli_cmd = cli_commands.get(cmd_name)
        
        if not cli_cmd:
            print(f"Warning: CLI command '{cmd_name}' not found for function '{func_name}'")
            continue
        
        api_path = api_meta["path"]
        if api_path not in paths:
            paths[api_path] = {}
        
        # Extract path parameters
        path_params = extract_path_parameters(api_path)
        
        for method in api_meta["methods"]:
            method_lower = method.lower()
            
            # Generate parameters
            parameters = []
            
            # Add path parameters
            for path_param in path_params:
                parameters.append({
                    "name": path_param,
                    "in": "path", 
                    "required": True,
                    "description": f"{path_param.title()} identifier",
                    "schema": {"type": "string"}
                })
            
            # Add query parameters from CLI options
            for cli_param in cli_cmd.get("params", []):
                if cli_param["is_option"] and cli_param["name"] not in path_params:
                    # Skip CLI-specific parameters
                    if cli_param["name"] in ["path", "config"]:
                        continue
                    parameters.append(generate_parameter_schema(cli_param, is_path_param=False))
            
            # Generate operation
            operation = {
                "summary": api_meta["summary"],
                "description": api_meta["summary"],
                "tags": api_meta["tags"],
                "parameters": parameters,
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {"type": "object"},
                                        "status": {"type": "string", "example": "success"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    },
                    "404": {
                        "description": "Not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
            
            # Add server specification for unversioned endpoints
            if api_path.startswith("/health") or not api_path.startswith("/projects") and not api_path.startswith("/schemas"):
                operation["servers"] = [
                    {
                        "url": "http://127.0.0.1:8623",
                        "description": "Unversioned endpoint - 127.0.0.1"
                    },
                    {
                        "url": "http://localhost:8623",
                        "description": "Unversioned endpoint - localhost"
                    }
                ]
            
            paths[api_path][method_lower] = operation
    
    return paths


def load_api_config() -> Dict[str, Any]:
    """Load API configuration from pyproject.toml."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            print("Warning: tomllib/tomli not available, using default config")
            return {"version": "v0"}
    
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return {"version": "v0"}  # Default config
    
    try:
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
            
        # Extract API generation config
        api_config = config.get("tool", {}).get("rpax", {}).get("api_generation", {})
        
        return {
            "version": api_config.get("version", "v0"),
            "base_path": api_config.get("base_path", "/api"),
            "title": api_config.get("title", "rpax API"),
            "description": api_config.get("description", "UiPath project analysis API - generated from CLI blueprint")
        }
    except Exception as e:
        print(f"Warning: Could not load pyproject.toml config: {e}")
        return {"version": "v0"}


def generate_openapi_spec() -> Dict[str, Any]:
    """Generate complete OpenAPI specification."""
    # Load configuration and data
    api_config = load_api_config()
    cli_data = load_cli_reference()
    decorator_metadata = extract_decorator_metadata()
    
    api_version = api_config["version"]
    print(f"Found {len(decorator_metadata)} API-enabled commands")
    print(f"Generating OpenAPI spec for API version: {api_version}")
    
    # Generate OpenAPI specification
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": api_config.get("title", "rpax API"),
            "description": api_config.get("description", "UiPath project analysis API - generated from CLI blueprint"),
            "version": "0.1.0",  # Package version, different from API version
            "contact": {
                "name": "rpax",
                "url": "https://github.com/rpapub/rpax"
            },
            "license": {
                "name": "MIT",
                "url": "https://github.com/rpapub/rpax/blob/main/LICENSE"
            }
        },
        "servers": [
            {
                "url": f"http://127.0.0.1:8623{api_config.get('base_path', '/api')}/{api_version}",
                "description": "Local development server (versioned endpoints) - 127.0.0.1"
            },
            {
                "url": f"http://localhost:8623{api_config.get('base_path', '/api')}/{api_version}",
                "description": "Local development server (versioned endpoints) - localhost"
            },
            {
                "url": "http://127.0.0.1:8623",
                "description": "Local development server (unversioned endpoints) - 127.0.0.1"
            },
            {
                "url": "http://localhost:8623",
                "description": "Local development server (unversioned endpoints) - localhost"
            }
        ],
        "paths": generate_openapi_paths(cli_data, decorator_metadata),
        "components": {
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "message": {"type": "string"},
                        "status": {"type": "string", "example": "error"}
                    },
                    "required": ["error", "message", "status"]
                }
            }
        }
    }
    
    return spec


def main():
    """Generate OpenAPI specification and write to versioned docs/api/vX/openapi.yaml."""
    try:
        print("Generating OpenAPI specification...")
        spec = generate_openapi_spec()
        
        # Get API version for versioned output path
        api_config = load_api_config()
        api_version = api_config["version"]
        
        # Create versioned output directory
        output_dir = Path(f"docs/api/{api_version}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine output format based on yaml availability
        if yaml is not None:
            output_path = output_dir / "openapi.yaml"
            with open(output_path, 'w') as f:
                yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
            format_msg = "YAML"
        else:
            output_path = output_dir / "openapi.json"
            with open(output_path, 'w') as f:
                json.dump(spec, f, indent=2)
            format_msg = "JSON (install PyYAML for YAML output)"
        
        print(f"[OK] Generated OpenAPI specification: {output_path}")
        print(f"   - API version: {api_version}")
        print(f"   - {len(spec['paths'])} API paths")
        print(f"   - Format: {format_msg}")
        print(f"   - Generated from CLI blueprint decorators")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Error generating OpenAPI spec: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())