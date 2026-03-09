"""Message-of-the-Day utility for rpa-cli.

Fetches a JSON MOTD from GitHub (raw), caches locally for 24 h, and displays
an active entry (date-filtered) once per day via rich Panel.  All errors are
silently swallowed — MOTD must never crash the CLI.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

MOTD_URL = (
    "https://raw.githubusercontent.com/rpapub/rpax/motd/motd.json"
)
_CACHE_TTL_SECONDS = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_path() -> Path:
    """Return OS-appropriate cache file path."""
    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA")
        base = Path(local_app) if local_app else Path.home() / ".cache"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "rpa-cli" / "motd-cache.json"


def _is_cache_fresh(path: Path) -> bool:
    """Return True if *path* exists and was modified less than 24 h ago."""
    try:
        return (time.time() - path.stat().st_mtime) < _CACHE_TTL_SECONDS
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Network fetch
# ---------------------------------------------------------------------------


def _fetch_motd(url: str = MOTD_URL, timeout: int = 3) -> list[dict] | None:
    """GET *url* and return parsed JSON list, or None on any error.

    Runs inside a daemon thread so DNS resolution (which ignores socket timeout)
    cannot block the CLI indefinitely.
    """
    result: list[list[dict] | None] = [None]

    def _do_fetch() -> None:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                result[0] = data
        except Exception:  # noqa: BLE001
            pass

    thread = threading.Thread(target=_do_fetch, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    return result[0]


# ---------------------------------------------------------------------------
# Load (cache-aware)
# ---------------------------------------------------------------------------


def _load_motd() -> list[dict]:
    """Return MOTD list from cache (if fresh) or network; never raises."""
    cache = _cache_path()

    if _is_cache_fresh(cache):
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            pass  # fall through to fetch

    fetched = _fetch_motd()
    if fetched is not None:
        # Atomic write: tmp → rename
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache.with_suffix(".tmp")
            tmp.write_text(json.dumps(fetched), encoding="utf-8")
            tmp.replace(cache)
        except OSError:
            pass  # cache write failed — not fatal
        return fetched

    # Fetch failed — return stale cache if available
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass

    return []


# ---------------------------------------------------------------------------
# Date filtering
# ---------------------------------------------------------------------------


def get_active_message(today: date | None = None) -> dict | None:
    """Return the first MOTD entry active on *today*, or None."""
    if today is None:
        today = datetime.now().date()

    entries = _load_motd()
    for entry in entries:
        try:
            from_date = date.fromisoformat(entry["from"])
            thru_date = date.fromisoformat(entry["thru"])
            if from_date <= today <= thru_date:
                return entry
        except (KeyError, ValueError, TypeError):
            continue
    return None


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def show_motd(console: Console) -> None:
    """Print MOTD panel if an active message exists.  Silently no-ops on error."""
    try:
        entry = get_active_message()
        if entry is None:
            return
        body = entry.get("message", "")
        url = entry.get("url", "")
        content = body
        if url:
            content = f"{body}\n{url}"
        console.print(
            Panel(
                content,
                title="[bold]📢 rpa-cli[/bold]",
                style="dim cyan",
                expand=False,
            )
        )
    except Exception:  # noqa: BLE001
        pass
