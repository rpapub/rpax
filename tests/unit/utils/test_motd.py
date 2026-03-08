"""Unit tests for rpax.utils.motd."""

import json
import time
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rpax.utils.motd import (
    _cache_path,
    _fetch_motd,
    _is_cache_fresh,
    _load_motd,
    get_active_message,
    show_motd,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ENTRIES = [
    {
        "from": "2026-03-01",
        "thru": "2026-03-31",
        "message": "Test announcement",
        "url": "https://example.com/",
    },
    {
        "from": "2026-04-01",
        "thru": "2026-04-30",
        "message": "April announcement",
    },
]


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------


def test_cache_path_is_path():
    p = _cache_path()
    assert isinstance(p, Path)
    assert p.name == "motd-cache.json"
    assert "rpa-cli" in str(p)


# ---------------------------------------------------------------------------
# _is_cache_fresh
# ---------------------------------------------------------------------------


def test_is_cache_fresh_missing_file(tmp_path):
    assert _is_cache_fresh(tmp_path / "nonexistent.json") is False


def test_is_cache_fresh_new_file(tmp_path):
    f = tmp_path / "cache.json"
    f.write_text("[]")
    assert _is_cache_fresh(f) is True


def test_is_cache_fresh_old_file(tmp_path):
    f = tmp_path / "cache.json"
    f.write_text("[]")
    # Backdate mtime by 25 hours
    old_mtime = time.time() - 90_000
    import os

    os.utime(f, (old_mtime, old_mtime))
    assert _is_cache_fresh(f) is False


# ---------------------------------------------------------------------------
# _fetch_motd
# ---------------------------------------------------------------------------


def test_fetch_motd_returns_list_on_success():
    payload = json.dumps(SAMPLE_ENTRIES).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _fetch_motd("http://fake/motd.json")

    assert result == SAMPLE_ENTRIES


def test_fetch_motd_returns_none_on_network_error():
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no net")):
        result = _fetch_motd("http://fake/motd.json")
    assert result is None


def test_fetch_motd_returns_none_on_bad_json():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not json{"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _fetch_motd("http://fake/motd.json")
    assert result is None


def test_fetch_motd_returns_none_when_response_is_dict():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"key": "value"}'
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = _fetch_motd("http://fake/motd.json")
    assert result is None


# ---------------------------------------------------------------------------
# _load_motd
# ---------------------------------------------------------------------------


def test_load_motd_uses_fresh_cache(tmp_path):
    cache = tmp_path / "motd-cache.json"
    cache.write_text(json.dumps(SAMPLE_ENTRIES))

    with patch("rpax.utils.motd._cache_path", return_value=cache), patch(
        "rpax.utils.motd._fetch_motd"
    ) as mock_fetch:
        result = _load_motd()

    mock_fetch.assert_not_called()
    assert result == SAMPLE_ENTRIES


def test_load_motd_fetches_when_cache_stale(tmp_path):
    cache = tmp_path / "motd-cache.json"
    cache.write_text(json.dumps([]))
    # Make it stale
    old_mtime = time.time() - 90_000
    import os

    os.utime(cache, (old_mtime, old_mtime))

    with patch("rpax.utils.motd._cache_path", return_value=cache), patch(
        "rpax.utils.motd._fetch_motd", return_value=SAMPLE_ENTRIES
    ):
        result = _load_motd()

    assert result == SAMPLE_ENTRIES
    # Cache should have been updated
    assert json.loads(cache.read_text()) == SAMPLE_ENTRIES


def test_load_motd_returns_stale_cache_on_fetch_failure(tmp_path):
    cache = tmp_path / "motd-cache.json"
    cache.write_text(json.dumps(SAMPLE_ENTRIES))
    old_mtime = time.time() - 90_000
    import os

    os.utime(cache, (old_mtime, old_mtime))

    with patch("rpax.utils.motd._cache_path", return_value=cache), patch(
        "rpax.utils.motd._fetch_motd", return_value=None
    ):
        result = _load_motd()

    assert result == SAMPLE_ENTRIES


def test_load_motd_returns_empty_on_no_cache_and_fetch_failure(tmp_path):
    cache = tmp_path / "motd-cache.json"

    with patch("rpax.utils.motd._cache_path", return_value=cache), patch(
        "rpax.utils.motd._fetch_motd", return_value=None
    ):
        result = _load_motd()

    assert result == []


# ---------------------------------------------------------------------------
# get_active_message
# ---------------------------------------------------------------------------


def test_get_active_message_matches_today():
    with patch("rpax.utils.motd._load_motd", return_value=SAMPLE_ENTRIES):
        result = get_active_message(today=date(2026, 3, 15))
    assert result is not None
    assert result["message"] == "Test announcement"


def test_get_active_message_on_boundary_from():
    with patch("rpax.utils.motd._load_motd", return_value=SAMPLE_ENTRIES):
        result = get_active_message(today=date(2026, 3, 1))
    assert result is not None


def test_get_active_message_on_boundary_thru():
    with patch("rpax.utils.motd._load_motd", return_value=SAMPLE_ENTRIES):
        result = get_active_message(today=date(2026, 3, 31))
    assert result is not None


def test_get_active_message_before_range():
    with patch("rpax.utils.motd._load_motd", return_value=SAMPLE_ENTRIES):
        result = get_active_message(today=date(2026, 2, 28))
    assert result is None


def test_get_active_message_after_range():
    with patch("rpax.utils.motd._load_motd", return_value=SAMPLE_ENTRIES):
        result = get_active_message(today=date(2026, 5, 1))
    assert result is None


def test_get_active_message_returns_first_match():
    entries = [
        {"from": "2026-03-01", "thru": "2026-03-31", "message": "First"},
        {"from": "2026-03-01", "thru": "2026-03-31", "message": "Second"},
    ]
    with patch("rpax.utils.motd._load_motd", return_value=entries):
        result = get_active_message(today=date(2026, 3, 10))
    assert result["message"] == "First"


def test_get_active_message_skips_malformed_entries():
    entries = [
        {"from": "bad-date", "thru": "2026-03-31", "message": "Broken"},
        {"from": "2026-03-01", "thru": "2026-03-31", "message": "Good"},
    ]
    with patch("rpax.utils.motd._load_motd", return_value=entries):
        result = get_active_message(today=date(2026, 3, 10))
    assert result["message"] == "Good"


def test_get_active_message_empty_list():
    with patch("rpax.utils.motd._load_motd", return_value=[]):
        result = get_active_message(today=date(2026, 3, 10))
    assert result is None


# ---------------------------------------------------------------------------
# show_motd
# ---------------------------------------------------------------------------


def test_show_motd_prints_panel_when_active():
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    console = Console(file=buf, width=80)

    active = SAMPLE_ENTRIES[0]
    with patch("rpax.utils.motd.get_active_message", return_value=active):
        show_motd(console)

    output = buf.getvalue()
    assert "Test announcement" in output
    assert "https://example.com/" in output


def test_show_motd_prints_nothing_when_no_active():
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    console = Console(file=buf, width=80)

    with patch("rpax.utils.motd.get_active_message", return_value=None):
        show_motd(console)

    assert buf.getvalue() == ""


def test_show_motd_swallows_exceptions():
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    console = Console(file=buf, width=80)

    with patch("rpax.utils.motd.get_active_message", side_effect=RuntimeError("boom")):
        # Must not raise
        show_motd(console)
