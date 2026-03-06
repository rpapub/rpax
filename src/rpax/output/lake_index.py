"""Lake index generator for multi-project discovery."""

import json
from datetime import UTC, datetime
from pathlib import Path


class LakeIndexGenerator:
    """Generates a top-level index of all projects in a lake directory."""

    def __init__(self, lake_root: Path) -> None:
        self.lake_root = lake_root

    def build_lake_index(self) -> dict:
        """Scan lake directory and build index from manifest files."""
        projects = []
        for manifest_path in sorted(self.lake_root.glob("*/manifest.json")):
            try:
                with manifest_path.open() as f:
                    manifest = json.load(f)
                projects.append({
                    "projectSlug": manifest_path.parent.name,
                    "projectName": manifest.get("projectName"),
                    "projectType": manifest.get("projectType"),
                    "projectVersion": manifest.get("projectVersion"),
                    "generatedAt": manifest.get("generatedAt"),
                    "totalWorkflows": manifest.get("totalWorkflows", 0),
                    "parseErrors": manifest.get("parseErrors", 0),
                    "artifactDir": str(manifest_path.parent.relative_to(self.lake_root)),
                })
            except Exception:
                continue

        return {
            "generatedAt": datetime.now(UTC).isoformat(),
            "lakeRoot": str(self.lake_root),
            "totalProjects": len(projects),
            "projects": projects,
        }

    def save_lake_index(self) -> Path:
        """Write lake.index.json to the lake root and return its path."""
        index = self.build_lake_index()
        output_path = self.lake_root / "lake.index.json"
        with output_path.open("w") as f:
            json.dump(index, f, indent=2)
        return output_path
