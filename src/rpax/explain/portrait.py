"""Bay portrait renderer for the `rpax view` command.

Produces a compact, information-dense project snapshot (~12 terminal lines)
using Unicode block characters as visual encodings.
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.text import Text

# Unicode density characters (sparse → dense)
_DENSITY = ["·", "░", "▒", "▓", "█"]

# Sparkline vertical bar characters
_SPARK = "▁▂▃▄▅▆▇█"

# Folder colors cycling through Rich terminal colors
_FOLDER_COLORS = ["cyan", "green", "yellow", "magenta", "blue", "red"]

# Block-fill chars for mini-bars
_BAR_FULL = "█"
_BAR_HALF = "▒"
_BAR_EMPTY = "░"


def _density_char(count: int) -> str:
    """Map activity count to a Unicode density character."""
    if count == 0:
        return _DENSITY[0]
    elif count <= 3:
        return _DENSITY[1]
    elif count <= 8:
        return _DENSITY[2]
    elif count <= 20:
        return _DENSITY[3]
    else:
        return _DENSITY[4]


def _mini_bar(ratio: float, width: int = 10) -> str:
    """Render a left-filled block bar of given width from ratio 0.0–1.0.

    e.g. ratio=0.7, width=10 → '███████░░░'
    """
    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * width)
    empty = width - filled
    return _BAR_FULL * filled + _BAR_EMPTY * empty


class BayPortrait:
    """Loads and aggregates bay artifact data for the view command."""

    def __init__(self, artifacts_dir: Path) -> None:
        self._dir = artifacts_dir
        self._manifest: dict = {}
        self._call_graph: dict = {}
        self._workflows_index: dict = {}
        self._metrics: list[dict] = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load all relevant artifacts from disk (graceful on missing files)."""
        self._manifest = self._load_json("manifest.json") or {}
        self._call_graph = self._load_json("call-graph.json") or {}
        self._workflows_index = self._load_json("workflows.index.json") or {}
        self._metrics = self._load_metrics()

    def _load_json(self, filename: str) -> dict | None:
        path = self._dir / filename
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _load_metrics(self) -> list[dict]:
        """Recursively load all metrics/*.json files."""
        metrics_dir = self._dir / "metrics"
        if not metrics_dir.exists():
            return []
        results: list[dict] = []
        for path in metrics_dir.rglob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        results.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return results

    # ------------------------------------------------------------------
    # Computed dimensions
    # ------------------------------------------------------------------

    def _depth_histogram(self) -> dict[int, int]:
        """Return dict of call_depth → workflow count."""
        histogram: dict[int, int] = {}
        workflows = self._call_graph.get("workflows", {})
        for node in workflows.values():
            depth = node.get("call_depth", 0)
            # Clamp negative depths (orphans) to 0 for display
            depth = max(0, depth)
            histogram[depth] = histogram.get(depth, 0) + 1
        return histogram

    def _folder_counts(self) -> dict[str, int]:
        """Return dict of top-level folder → workflow count."""
        counts: dict[str, int] = {}
        workflows = self._workflows_index.get("workflows", [])
        for wf in workflows:
            rel = wf.get("relativePath", "") or wf.get("filePath", "")
            rel = rel.replace("\\", "/")
            parts = rel.split("/")
            folder = parts[0] if len(parts) > 1 else "(root)"
            counts[folder] = counts.get(folder, 0) + 1
        return counts

    def _signature_chars(self) -> list[int]:
        """Return sorted list of totalActivities per workflow (ascending)."""
        workflows = self._workflows_index.get("workflows", [])
        counts = [wf.get("totalActivities", 0) or 0 for wf in workflows]
        return sorted(counts)

    def _style_dimensions(self) -> dict[str, float]:
        """Compute 4 style ratios, each 0.0–1.0.

        Returns:
            orchestration: invoke / (invoke + selector), 1.0 = full orchestration
            deep:          0.0 = flat (depth ≤ 2), 1.0 = deep (depth > 6)
            documented:    annotated / total nodes ratio
            defensive:     tryCatch / total workflows ratio (clamped to 1.0)
        """
        total_invoke = sum(m.get("invokeCount", 0) for m in self._metrics)
        total_selector = sum(m.get("selectorCount", 0) for m in self._metrics)
        total_trycatch = sum(m.get("tryCatchCount", 0) for m in self._metrics)
        total_annotated = sum(m.get("annotatedActivityCount", 0) for m in self._metrics)
        total_nodes = sum(m.get("totalNodes", 0) for m in self._metrics)

        cg_metrics = self._call_graph.get("metrics", {})
        max_depth = cg_metrics.get("max_call_depth", 0)

        invoke_selector = total_invoke + total_selector
        orchestration = (total_invoke / invoke_selector) if invoke_selector > 0 else 0.5

        # Deep: map max_depth 0–8+ to 0.0–1.0
        deep = min(1.0, max_depth / 8.0) if max_depth > 0 else 0.0

        documented = (total_annotated / total_nodes) if total_nodes > 0 else 0.0

        wf_count = len(self._workflows_index.get("workflows", []))
        defensive = min(1.0, (total_trycatch / wf_count)) if wf_count > 0 else 0.0

        return {
            "orchestration": orchestration,
            "deep": deep,
            "documented": documented,
            "defensive": defensive,
        }

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_depth_sparkline(self, histogram: dict[int, int], max_depth: int) -> str:
        """Render depth distribution as a single-row sparkline."""
        if not histogram:
            return "·"
        max_count = max(histogram.values()) if histogram else 1
        chars = []
        for d in range(max_depth + 1):
            count = histogram.get(d, 0)
            if count == 0:
                chars.append("·")
            else:
                idx = min(7, round((count / max_count) * 7))
                chars.append(_SPARK[idx])
        return " ".join(chars)

    def _render_signature_strip(self, width: int) -> Text:
        """Render the workflow signature strip as a Rich Text object."""
        counts = self._signature_chars()
        if not counts:
            return Text("(no workflows)", style="dim")

        # Map to density chars with folder colors
        workflows = self._workflows_index.get("workflows", [])
        # Build sorted list of (totalActivities, folder) tuples
        wf_data = []
        for wf in workflows:
            act = wf.get("totalActivities", 0) or 0
            rel = wf.get("relativePath", "") or wf.get("filePath", "")
            rel = rel.replace("\\", "/")
            parts = rel.split("/")
            folder = parts[0] if len(parts) > 1 else "(root)"
            wf_data.append((act, folder))
        wf_data.sort(key=lambda x: x[0])

        # Build folder → color map
        seen_folders: dict[str, str] = {}
        color_idx = 0

        strip = Text()
        for act, folder in wf_data[:width]:
            char = _density_char(act)
            if folder not in seen_folders:
                seen_folders[folder] = _FOLDER_COLORS[color_idx % len(_FOLDER_COLORS)]
                color_idx += 1
            strip.append(char, style=seen_folders[folder])

        return strip

    def _render_style_row(self, label_l: str, label_r: str, ratio: float, bar_width: int = 8) -> str:
        """Render one style dimension as 'LeftLabel BAR RightLabel'."""
        bar = _mini_bar(ratio, bar_width)
        return f"{label_l:<14} {bar} {label_r}"

    # ------------------------------------------------------------------
    # Public render
    # ------------------------------------------------------------------

    def render(self, console: Console, width: int = 80) -> None:
        """Render the bay portrait to the console."""
        # ── gather data ──────────────────────────────────────────────
        m = self._manifest
        project_name = m.get("projectName", "Unknown")
        project_type = m.get("projectType", "?")
        project_version = m.get("projectVersion", "")
        generated_at = (m.get("generatedAt", "") or "")[:10]  # date only
        _pe = m.get("parseErrors", 0)
        parse_errors = _pe if isinstance(_pe, int) else len(_pe)

        cg = self._call_graph.get("metrics", {})
        total_wf = cg.get("total_workflows", 0) or len(
            self._workflows_index.get("workflows", [])
        )
        total_dep = cg.get("total_dependencies", 0)
        entry_pts = cg.get("entry_points", 0)
        orphans = cg.get("orphaned_workflows", 0)
        max_depth = cg.get("max_call_depth", 0)

        histogram = self._depth_histogram()
        folder_counts = self._folder_counts()
        style = self._style_dimensions()

        inner_width = width - 4  # inside the border chars "│ … │"

        # ── border helpers ────────────────────────────────────────────
        def border_top(title: str, right: str) -> str:
            left_part = f"┌─ {title} "
            right_part = f" {right} ─┐"
            fill = width - len(left_part) - len(right_part)
            return left_part + "─" * max(0, fill) + right_part

        def border_mid() -> str:
            return "├" + "─" * (width - 2) + "┤"

        def border_bot() -> str:
            return "└" + "─" * (width - 2) + "┘"

        def pad_line(content: str) -> str:
            """Wrap content in │ … │, padding to width."""
            padded = content.ljust(inner_width)[:inner_width]
            return f"│ {padded} │"

        # ── line 1: header ────────────────────────────────────────────
        right_header = f"{project_type} · v{project_version} · {generated_at}"
        console.print(border_top(project_name, right_header))

        # ── line 2: stats ─────────────────────────────────────────────
        stats = (
            f"{total_wf} wf   {total_dep} deps   {entry_pts} entries   "
            f"depth:{max_depth}   {orphans} orphans   {parse_errors} errors"
        )
        console.print(pad_line(stats))

        # ── line 3: separator ─────────────────────────────────────────
        console.print(border_mid())

        # ── lines 4–6: depth sparkline + folder breakdown ─────────────
        # Folder column: top folders sorted by count descending
        sorted_folders = sorted(folder_counts.items(), key=lambda x: -x[1])

        # Build depth block (3 lines): header, sparkline, counts
        depth_col_width = inner_width // 2
        folder_col_width = inner_width - depth_col_width - 2  # 2 for spacing

        max_d = max(histogram.keys()) if histogram else 0
        max_hist = max(histogram.values()) if histogram else 1

        spark_chars = " ".join(
            _SPARK[min(7, round((histogram.get(d, 0) / max_hist) * 7))]
            if histogram.get(d, 0) > 0
            else "·"
            for d in range(max_d + 1)
        )
        counts_str = " ".join(str(histogram.get(d, 0)) for d in range(max_d + 1))

        depth_lines = [
            f"{'DEPTH':<{depth_col_width}}",
            f"  {spark_chars}"[:depth_col_width].ljust(depth_col_width),
            f"  {counts_str}"[:depth_col_width].ljust(depth_col_width),
        ]

        folder_lines = ["FOLDERS".ljust(folder_col_width)]
        bar_room = max(4, folder_col_width - 20)  # leave space for name + count
        max_folder_cnt = max(folder_counts.values()) if folder_counts else 1
        for folder, cnt in sorted_folders[:2]:
            ratio = cnt / max_folder_cnt
            bar_len = max(1, round(ratio * bar_room))
            bar = "█" * bar_len
            folder_lines.append(f"{folder[:10]:<10} {bar:<{bar_room}} {cnt}")

        for i in range(3):
            dl = depth_lines[i] if i < len(depth_lines) else " " * depth_col_width
            fl = folder_lines[i] if i < len(folder_lines) else ""
            line = f"{dl}  {fl}"
            console.print(pad_line(line))

        # ── line 7: signature label ───────────────────────────────────
        console.print(pad_line("SIGNATURE  (each char = 1 workflow, shade = activity density)"))

        # ── line 8: signature strip ───────────────────────────────────
        strip = self._render_signature_strip(inner_width)
        strip_len = sum(len(s) for s in strip._spans) or len(strip.plain)
        padding = " " * max(0, inner_width - len(strip.plain))
        # Print as padded panel line manually
        console.print("│ ", end="")
        console.print(strip, end="")
        console.print(padding + " │")

        # ── lines 9–10: style dimensions ─────────────────────────────
        console.print(pad_line("STYLE"))

        orch_row = self._render_style_row(
            "Orchestration", "UI", style["orchestration"], bar_width=10
        )
        doc_row = self._render_style_row(
            "Documented", "Bare", style["documented"], bar_width=10
        )
        line9 = f"{orch_row}   {doc_row}"
        console.print(pad_line(line9))

        deep_row = self._render_style_row(
            "Deep", "Flat", style["deep"], bar_width=10
        )
        def_row = self._render_style_row(
            "Defensive", "Bare", style["defensive"], bar_width=10
        )
        line10 = f"{deep_row}   {def_row}"
        console.print(pad_line(line10))

        # ── bottom border ─────────────────────────────────────────────
        console.print(border_bot())
