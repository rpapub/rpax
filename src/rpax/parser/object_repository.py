"""Object Repository adapter using cpmf-uips-or library.

Thin wrapper over cpmf_uips_or.discover_inventory / find_objects_dir.
The richer model (apps → versions → screens → elements) is exposed directly
from the external library; this module just provides a single entry point.
"""

from pathlib import Path

from cpmf_uips_or import discover_inventory, find_objects_dir
from cpmf_uips_or.models import ElementEntry, Inventory, ScreenEntry

__all__ = [
    "parse_object_repository",
    "find_objects_dir",
    "Inventory",
    "ScreenEntry",
    "ElementEntry",
]


def parse_object_repository(project_root: Path) -> Inventory:
    """Parse Object Repository from project root.

    Args:
        project_root: Root directory of UiPath project (where project.json lives)

    Returns:
        Inventory with apps, screens, and elements (empty if no .objects dir)
    """
    objects_dir = project_root / ".objects"
    return discover_inventory(objects_dir)
