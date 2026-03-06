"""Archive index generator for multi-record discovery."""

import json
from datetime import UTC, datetime
from pathlib import Path


class WarehouseIndexGenerator:
    """Generates a top-level index of all records in an archive directory."""

    def __init__(self, warehouse_root: Path) -> None:
        self.warehouse_root = warehouse_root

    def build_warehouse_index(self) -> dict:
        """Scan archive directory and build index from manifest files."""
        records = []
        for manifest_path in sorted(self.warehouse_root.glob("*/manifest.json")):
            try:
                with manifest_path.open() as f:
                    manifest = json.load(f)
                records.append({
                    "recordId": manifest_path.parent.name,
                    "projectName": manifest.get("projectName"),
                    "projectType": manifest.get("projectType"),
                    "projectVersion": manifest.get("projectVersion"),
                    "generatedAt": manifest.get("generatedAt"),
                    "totalWorkflows": manifest.get("totalWorkflows", 0),
                    "parseErrors": manifest.get("parseErrors", 0),
                    "artifactDir": str(manifest_path.parent.relative_to(self.warehouse_root)),
                })
            except Exception:
                continue

        return {
            "generatedAt": datetime.now(UTC).isoformat(),
            "archiveRoot": str(self.warehouse_root),
            "totalRecords": len(records),
            "records": records,
        }

    def save_warehouse_index(self) -> Path:
        """Write warehouse.index.json to the archive root and return its path."""
        index = self.build_warehouse_index()
        output_path = self.warehouse_root / "warehouse.index.json"
        with output_path.open("w") as f:
            json.dump(index, f, indent=2)
        return output_path
