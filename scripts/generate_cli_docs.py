#!/usr/bin/env python3
"""
Generate CLI documentation by running rpax help commands.

This script extracts all commands, subcommands, options, and help text
by executing the CLI with --help flags and parsing the output.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import re


def run_help_command(command):
    """Run rpax command with --help and return output."""
    try:
        result = subprocess.run(
            ["uv", "run", "rpax"] + command + ["--help"], 
            capture_output=True, 
            text=True, 
            cwd=Path(__file__).parent.parent
        )
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Error running {' '.join(command)}: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception running {' '.join(command)}: {e}")
        return None


def parse_help_output(help_text, command_name):
    """Parse help output into structured information."""
    lines = help_text.strip().split('\n')
    
    # Extract description (usually after "Usage:" and before options)
    description = ""
    in_description = False
    
    usage_line = ""
    options = []
    commands = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Find usage line
        if line.startswith("Usage:"):
            usage_line = line.replace("Usage:", "").strip()
        
        # Find description (text before Options/Commands sections)
        elif not line.startswith("Usage:") and not line.startswith("Options:") and not line.startswith("Commands:") and line and not in_description:
            if description:
                description += " " + line
            else:
                description = line
        
        # Parse Options section
        elif line == "Options:":
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("Commands:") and lines[i].strip():
                opt_line = lines[i].strip()
                if opt_line and not opt_line.startswith("Commands:"):
                    # Parse option line like: "-v, --verbose    Enable verbose output"
                    if re.match(r'\s*-', opt_line):
                        parts = re.split(r'\s{2,}', opt_line, 1)  # Split on multiple spaces
                        if len(parts) >= 2:
                            option_flags = parts[0].strip()
                            option_help = parts[1].strip()
                            options.append({
                                "flags": option_flags,
                                "help": option_help
                            })
                i += 1
            i -= 1  # Back up one since loop will increment
        
        # Parse Commands section
        elif line == "Commands:":
            i += 1
            while i < len(lines) and lines[i].strip():
                cmd_line = lines[i].strip()
                if cmd_line:
                    # Parse command line like: "parse     Parse UiPath project"
                    parts = re.split(r'\s{2,}', cmd_line, 1)  # Split on multiple spaces
                    if len(parts) >= 2:
                        cmd_name = parts[0].strip()
                        cmd_help = parts[1].strip()
                        commands.append({
                            "name": cmd_name,
                            "help": cmd_help
                        })
                i += 1
            i -= 1  # Back up one since loop will increment
        
        i += 1
    
    return {
        "name": command_name,
        "description": description,
        "usage": usage_line,
        "options": options,
        "subcommands": commands
    }


def generate_markdown_docs(main_help, subcommand_helps, version="0.0.1"):
    """Generate markdown documentation from parsed help data."""
    
    docs = f"""# rpax CLI Command Reference

**Version**: {version}  
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Generator**: CLI help output parsing

This document provides comprehensive reference for all rpax CLI commands, options, and usage patterns.

## Overview

{main_help.get('description', 'rpax is a code-first CLI tool that parses UiPath Process and Library projects into JSON call graphs, arguments, and diagrams for documentation, validation, and CI impact analysis.')}

## Main Command

### `rpax`

**Usage**: `{main_help.get('usage', 'rpax [OPTIONS] COMMAND [ARGS]...')}`

{main_help.get('description', '')}

"""

    # Main command options
    if main_help.get('options'):
        docs += "#### Global Options\n\n"
        for option in main_help['options']:
            docs += f"- `{option['flags']}` - {option['help']}\n"
        docs += "\n"

    # Subcommands
    if main_help.get('subcommands'):
        docs += "## Available Commands\n\n"
        
        for subcmd in main_help['subcommands']:
            cmd_name = subcmd['name']
            docs += f"### `rpax {cmd_name}`\n\n"
            docs += f"{subcmd['help']}\n\n"
            
            # Get detailed help for this subcommand
            if cmd_name in subcommand_helps:
                subcmd_help = subcommand_helps[cmd_name]
                
                docs += f"**Usage**: `{subcmd_help.get('usage', f'rpax {cmd_name} [OPTIONS]')}`\n\n"
                
                if subcmd_help.get('description') and subcmd_help['description'] != subcmd['help']:
                    docs += f"{subcmd_help['description']}\n\n"
                
                # Subcommand options
                if subcmd_help.get('options'):
                    docs += "#### Options\n\n"
                    for option in subcmd_help['options']:
                        docs += f"- `{option['flags']}` - {option['help']}\n"
                    docs += "\n"
                
                # Nested subcommands
                if subcmd_help.get('subcommands'):
                    docs += "#### Subcommands\n\n"
                    for nested_cmd in subcmd_help['subcommands']:
                        docs += f"- `{nested_cmd['name']}` - {nested_cmd['help']}\n"
                    docs += "\n"
            
            docs += "---\n\n"

    # Add footer with metadata
    docs += f"""
## Generated Documentation Metadata

- **rpax version**: {version}
- **Documentation generated**: {datetime.now().isoformat()}
- **Generator method**: CLI help output parsing
- **Commands documented**: {len(subcommand_helps) + 1}

## Usage Examples

### Basic Project Parsing
```bash
rpax parse /path/to/uipath/project
```

### View Available Projects
```bash  
rpax list --lake-path /path/to/.rpax-lake
```

### Generate Pseudocode
```bash
rpax pseudocode --project my-project-slug WorkflowName.xaml
```

### Show All Workflows  
```bash
rpax pseudocode --project my-project-slug --all
```

For more detailed examples and advanced usage, see the main rpax documentation.
"""
    
    return docs


def extract_typer_commands():
    """Extract command structure using Typer introspection."""
    try:
        # Import the CLI app
        from rpax.cli import app
        import click
        import typer.main
        
        # Build and get the Click command from Typer app
        click_app = typer.main.get_command(app)
        
        def extract_command_info(cmd, path=None):
            """Recursively extract command information."""
            path = path or []
            
            result = {
                "name": getattr(cmd, "name", "rpax"),
                "path": path,
                "help": getattr(cmd, "help", "") or getattr(cmd, "short_help", "") or "",
                "params": [],
                "subcommands": []
            }
            
            # Extract parameters
            for param in getattr(cmd, "params", []):
                param_info = {
                    "name": param.name,
                    "type": str(param.type),
                    "required": param.required,
                    "default": getattr(param, "default", None),
                    "help": getattr(param, "help", "") or "",
                    "is_flag": getattr(param, "is_flag", False),
                    "is_option": hasattr(param, "opts") and bool(param.opts),
                    "opts": getattr(param, "opts", [])
                }
                result["params"].append(param_info)
            
            # Extract subcommands if this is a group
            if hasattr(cmd, "commands"):
                for subcmd_name, subcmd in cmd.commands.items():
                    subcmd_path = path + [subcmd_name]
                    subcmd_info = extract_command_info(subcmd, subcmd_path)
                    result["subcommands"].append(subcmd_info)
            
            return result
        
        # Extract complete command tree
        command_tree = extract_command_info(click_app)
        
        return command_tree
        
    except Exception as e:
        print(f"Error with Typer introspection: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Generate CLI documentation and save to docs directory."""
    print("Extracting CLI command structure using Typer introspection...")
    
    # Get version from pyproject.toml
    version = "0.0.1"  # Default fallback
    
    try:
        # Try Typer introspection first
        command_tree = extract_typer_commands()
        
        if command_tree:
            # Save JSON structure
            docs_dir = Path(__file__).parent.parent / "docs"
            docs_dir.mkdir(exist_ok=True)
            
            # Enhanced JSON output
            json_output = {
                "version": version,
                "generated_at": datetime.now().isoformat(),
                "generator": "typer_introspection",
                "command_tree": command_tree
            }
            
            json_output_file = docs_dir / "cli-reference.json"
            with open(json_output_file, "w", encoding="utf-8") as f:
                import json
                json.dump(json_output, f, indent=2, default=str)
            
            print(f"Enhanced CLI documentation generated: {json_output_file}")
            
            # Count total commands
            def count_commands(node):
                count = 1
                for subcmd in node.get("subcommands", []):
                    count += count_commands(subcmd)
                return count
            
            total_commands = count_commands(command_tree)
            print(f"Commands documented: {total_commands}")
        
        # Fallback to help parsing if introspection fails
        if not command_tree:
            print("Falling back to help output parsing...")
            
            # Get main help
            main_help_text = run_help_command([])
            if not main_help_text:
                print("Failed to get main help output")
                return 1
            
            main_help = parse_help_output(main_help_text, "rpax")
            print(f"Found {len(main_help.get('subcommands', []))} main commands")
            
            # Get help for each subcommand
            subcommand_helps = {}
            if main_help.get('subcommands'):
                for subcmd in main_help['subcommands']:
                    cmd_name = subcmd['name']
                    print(f"Getting help for: {cmd_name}")
                    subcmd_help_text = run_help_command([cmd_name])
                    if subcmd_help_text:
                        subcommand_helps[cmd_name] = parse_help_output(subcmd_help_text, f"rpax {cmd_name}")
            
            # Generate markdown documentation
            docs_content = generate_markdown_docs(main_help, subcommand_helps, version)
            
            # Save to docs directory
            docs_dir = Path(__file__).parent.parent / "docs"
            docs_dir.mkdir(exist_ok=True)
            
            output_file = docs_dir / "cli-reference.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(docs_content)
            
            print(f"CLI documentation generated: {output_file}")
            print(f"Commands documented: {len(subcommand_helps) + 1}")
        
        print(f"rpax version: {version}")
        
    except Exception as e:
        print(f"Error generating CLI documentation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())