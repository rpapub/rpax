"""Output generators for rpax artifacts."""

from rpax.output.warehouse_index import WarehouseIndexGenerator
from rpax.output.lake_index import LakeIndexGenerator  # legacy

__all__ = ["WarehouseIndexGenerator", "LakeIndexGenerator"]
