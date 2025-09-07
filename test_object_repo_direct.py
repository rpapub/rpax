#!/usr/bin/env python3
"""Direct test of Object Repository parsing."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rpax.parser.object_repository import ObjectRepositoryParser

def main():
    parser = ObjectRepositoryParser()
    objects_path = Path("D:/github.com/rpapub/LuckyLawrencium/.objects")
    
    if not objects_path.exists():
        print(f"Object Repository path not found: {objects_path}")
        return
    
    print(f"Parsing Object Repository: {objects_path}")
    repository = parser.parse_repository(objects_path)
    
    if repository:
        print(f"OK Successfully parsed Object Repository")
        print(f"  Library ID: {repository.library_id}")
        print(f"  Library Type: {repository.library_type}")
        print(f"  Apps: {len(repository.apps)}")
        
        for app in repository.apps:
            print(f"    - {app.name} ({app.app_id}): {len(app.targets)} targets")
            for target in app.targets[:3]:  # Show first 3 targets
                print(f"      * {target.friendly_name} ({target.element_type})")
            if len(app.targets) > 3:
                print(f"      ... and {len(app.targets) - 3} more")
        
        # Generate MCP resources
        resources = parser.generate_mcp_resources(repository, "luckylawrencium-test")
        print(f"  Generated {len(resources)} MCP resources")
        
        # Save to file
        import json
        output_file = Path("test_object_repo_output.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "repository_summary": {
                    "library_id": repository.library_id,
                    "library_type": repository.library_type,
                    "apps_count": len(repository.apps),
                    "total_targets": sum(len(app.targets) for app in repository.apps)
                },
                "mcp_resources": resources
            }, f, indent=2)
        print(f"OK Saved results to {output_file}")
        
    else:
        print("ERROR Failed to parse Object Repository")

if __name__ == "__main__":
    main()