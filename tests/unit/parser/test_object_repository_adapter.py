"""Tests for the Object Repository thin adapter (cpmf-uips-or integration)."""

import pytest
from pathlib import Path
from unittest.mock import patch

from rpax.parser.object_repository import parse_object_repository
from cpmf_uips_or import Inventory


class TestObjectRepositoryAdapter:
    """Test that the thin adapter delegates to cpmf_uips_or correctly."""

    def test_parse_returns_inventory(self, tmp_path: Path) -> None:
        """parse_object_repository returns an Inventory (even with no .objects dir)."""
        result = parse_object_repository(tmp_path)
        assert isinstance(result, Inventory)

    def test_parse_empty_without_objects_dir(self, tmp_path: Path) -> None:
        """Returns empty Inventory when no .objects directory exists."""
        result = parse_object_repository(tmp_path)
        assert result.screens == []
        assert result.elements == []
        assert result.apps == []

    def test_parse_passes_objects_subdir(self, tmp_path: Path) -> None:
        """Adapter passes project_root/.objects to discover_inventory."""
        with patch("rpax.parser.object_repository.discover_inventory") as mock_discover:
            mock_discover.return_value = Inventory(screens=[], elements=[], apps=[])
            parse_object_repository(tmp_path)
            mock_discover.assert_called_once_with(tmp_path / ".objects")

    @pytest.mark.integration
    def test_parse_luckylawrencium(self) -> None:
        """Integration: parse a real Library corpus with Object Repository."""
        lucky_path = Path("D:/github.com/rpapub/LuckyLawrencium")
        if not lucky_path.exists():
            pytest.skip("LuckyLawrencium test project not available")

        inventory = parse_object_repository(lucky_path)

        assert isinstance(inventory, Inventory)
        assert len(inventory.apps) > 0
        assert len(inventory.screens) > 0
