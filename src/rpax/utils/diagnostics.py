"""Per-phase performance diagnostics for rpax.

Captures wall time (perf_counter_ns), CPU time (resource.getrusage),
Python memory delta (tracemalloc snapshots), and I/O block counts
for each named phase of artifact generation.

Note on RSS:
  - resource.ru_maxrss is NOT used: on Linux it stops updating after initial
    peak; on WSL2 it returns bytes instead of KB (microsoft/WSL#141).
  - VmRSS from /proc/self/status is read before and after each phase instead.
    Falls back to ru_maxrss (with documented caveats) on non-Linux systems.
"""

from __future__ import annotations

import resource
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ─── RSS helper ───────────────────────────────────────────────────────────────


def _read_proc_rss_kb() -> int:
    """Read current VmRSS from /proc/self/status (Linux/WSL2 only).

    Returns kilobytes. Falls back to resource.ru_maxrss on other platforms
    (unreliable on WSL2 — see module docstring).
    """
    if sys.platform == "linux":
        try:
            status = Path("/proc/self/status").read_text()
            for line in status.splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])  # already in kB
        except OSError:
            pass
    # Non-Linux fallback (macOS returns bytes, Linux KB — not normalised here)
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


# ─── Data model ───────────────────────────────────────────────────────────────


@dataclass
class PhaseResult:
    """Diagnostic metrics for one named phase of rpax artifact generation."""

    name: str
    wall_ns: int = 0          # perf_counter_ns delta
    cpu_user_s: float = 0.0   # ru_utime delta (seconds)
    cpu_sys_s: float = 0.0    # ru_stime delta (seconds)
    py_alloc_kb: int = 0      # tracemalloc net allocation delta (KB)
    py_peak_kb: int = 0       # tracemalloc peak within phase (KB)
    io_reads: int = 0         # ru_inblock delta (OS disk block reads)
    io_writes: int = 0        # ru_oublock delta (OS disk block writes)
    rss_before_kb: int = 0    # VmRSS before phase (KB)
    rss_after_kb: int = 0     # VmRSS after phase (KB)
    artifact_count: int = 0

    # Top Python allocators captured from tracemalloc (optional, only when
    # PhaseTimer is constructed with top_allocs > 0)
    top_allocators: list[dict] = field(default_factory=list)

    @property
    def wall_s(self) -> float:
        return self.wall_ns / 1_000_000_000

    @property
    def cpu_total_ms(self) -> float:
        return (self.cpu_user_s + self.cpu_sys_s) * 1000

    @property
    def delta_rss_kb(self) -> int:
        return self.rss_after_kb - self.rss_before_kb


# ─── Context manager ──────────────────────────────────────────────────────────


class PhaseTimer:
    """Context manager that captures wall time, CPU, memory, and I/O per phase.

    Usage::

        with PhaseTimer(top_allocs=5) as t:
            artifacts = self._generate_activities_artifacts(...)
        phases.append(t.result("activities", len(artifacts)))
    """

    def __init__(self, top_allocs: int = 0) -> None:
        """
        Args:
            top_allocs: If > 0, capture the top N Python allocators by size
                delta after the phase completes (via tracemalloc).
        """
        self._top_allocs = top_allocs
        self._t0 = self._t1 = 0
        self._res0: resource.struct_rusage | None = None
        self._res1: resource.struct_rusage | None = None
        self._rss0 = self._rss1 = 0
        self._snap0: tracemalloc.Snapshot | None = None
        self._snap1: tracemalloc.Snapshot | None = None
        self._py_peak_kb = 0

    def __enter__(self) -> "PhaseTimer":
        # Start or reset tracemalloc
        if tracemalloc.is_tracing():
            tracemalloc.clear_traces()
        else:
            tracemalloc.start(25)

        self._rss0 = _read_proc_rss_kb()
        self._res0 = resource.getrusage(resource.RUSAGE_SELF)
        self._snap0 = tracemalloc.take_snapshot()
        self._t0 = time.perf_counter_ns()
        return self

    def __exit__(self, *_: object) -> None:
        self._t1 = time.perf_counter_ns()
        self._res1 = resource.getrusage(resource.RUSAGE_SELF)
        self._rss1 = _read_proc_rss_kb()

        _, peak_bytes = tracemalloc.get_traced_memory()
        self._py_peak_kb = peak_bytes // 1024
        self._snap1 = tracemalloc.take_snapshot()

    def result(self, name: str, artifact_count: int = 0) -> PhaseResult:
        """Build a PhaseResult from captured measurements."""
        assert self._res0 and self._res1 and self._snap0 and self._snap1

        # Python allocation delta
        stats = self._snap1.compare_to(self._snap0, "lineno")
        net_bytes = sum(s.size_diff for s in stats)

        top: list[dict] = []
        if self._top_allocs > 0:
            for s in sorted(stats, key=lambda x: x.size_diff, reverse=True)[: self._top_allocs]:
                top.append(
                    {
                        "location": str(s.traceback[0]) if s.traceback else "?",
                        "size_delta_kb": s.size_diff // 1024,
                        "count_delta": s.count_diff,
                    }
                )

        return PhaseResult(
            name=name,
            wall_ns=self._t1 - self._t0,
            cpu_user_s=self._res1.ru_utime - self._res0.ru_utime,
            cpu_sys_s=self._res1.ru_stime - self._res0.ru_stime,
            py_alloc_kb=net_bytes // 1024,
            py_peak_kb=self._py_peak_kb,
            io_reads=self._res1.ru_inblock - self._res0.ru_inblock,
            io_writes=self._res1.ru_oublock - self._res0.ru_oublock,
            rss_before_kb=self._rss0,
            rss_after_kb=self._rss1,
            artifact_count=artifact_count,
            top_allocators=top,
        )


# ─── Formatting ───────────────────────────────────────────────────────────────


def format_phase_table(phases: list[PhaseResult], project_name: str = "") -> str:
    """Return a Rich-markup table string for console printing.

    Caller should pass the returned string to ``rich.console.Console().print()``.
    """
    try:
        from rich.table import Table
        from rich import box
    except ImportError:
        return _format_plain(phases, project_name)

    title = f"rpax bench — {project_name}" if project_name else "rpax bench"
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_footer=True)

    table.add_column("Phase", style="bold")
    table.add_column("Wall", justify="right")
    table.add_column("CPU (u+s)", justify="right")
    table.add_column("Py Δalloc", justify="right")
    table.add_column("VmRSS Δ", justify="right")
    table.add_column("I/O r/w", justify="right")
    table.add_column("Artifacts", justify="right")

    total_wall = sum(p.wall_ns for p in phases)
    total_cpu = sum(p.cpu_total_ms for p in phases)
    total_py = sum(p.py_alloc_kb for p in phases)
    total_rss = sum(p.delta_rss_kb for p in phases)
    total_ir = sum(p.io_reads for p in phases)
    total_iw = sum(p.io_writes for p in phases)
    total_art = sum(p.artifact_count for p in phases)

    for p in phases:
        rss_color = "red" if p.delta_rss_kb > 20_000 else "yellow" if p.delta_rss_kb > 5_000 else "green"
        table.add_row(
            p.name,
            f"{p.wall_s:.3f}s",
            f"{p.cpu_total_ms:.0f}ms",
            f"{'+' if p.py_alloc_kb >= 0 else ''}{p.py_alloc_kb // 1024:.1f} MB",
            f"[{rss_color}]{'+' if p.delta_rss_kb >= 0 else ''}{p.delta_rss_kb // 1024:.1f} MB[/{rss_color}]",
            f"{p.io_reads}/{p.io_writes}",
            str(p.artifact_count),
        )

    table.columns[1].footer = f"{total_wall / 1e9:.3f}s"
    table.columns[2].footer = f"{total_cpu:.0f}ms"
    table.columns[3].footer = f"{'+' if total_py >= 0 else ''}{total_py // 1024:.1f} MB"
    table.columns[4].footer = f"{'+' if total_rss >= 0 else ''}{total_rss // 1024:.1f} MB"
    table.columns[5].footer = f"{total_ir}/{total_iw}"
    table.columns[6].footer = str(total_art)

    # Render to string via Console
    import io
    from rich.console import Console

    buf = io.StringIO()
    con = Console(file=buf, highlight=False)
    con.print(table)
    return buf.getvalue()


def _format_plain(phases: list[PhaseResult], project_name: str = "") -> str:
    """Fallback plain-text table (no Rich dependency)."""
    lines = [f"rpax bench — {project_name}" if project_name else "rpax bench", ""]
    header = f"{'Phase':<22} {'Wall':>8} {'CPU(ms)':>9} {'PyΔ':>9} {'RSSΔ':>9} {'I/O r/w':>10} {'Art':>5}"
    lines.append(header)
    lines.append("-" * len(header))
    for p in phases:
        lines.append(
            f"{p.name:<22} {p.wall_s:>7.3f}s {p.cpu_total_ms:>8.0f} "
            f"{p.py_alloc_kb // 1024:>+8.1f}M {p.delta_rss_kb // 1024:>+8.1f}M "
            f"{p.io_reads:>5}/{p.io_writes:<4} {p.artifact_count:>5}"
        )
    return "\n".join(lines)


def phases_to_dict(phases: list[PhaseResult]) -> list[dict]:
    """Serialize phases to a JSON-compatible list of dicts."""
    return [
        {
            "name": p.name,
            "wall_s": round(p.wall_s, 4),
            "cpu_user_s": round(p.cpu_user_s, 4),
            "cpu_sys_s": round(p.cpu_sys_s, 4),
            "py_alloc_kb": p.py_alloc_kb,
            "py_peak_kb": p.py_peak_kb,
            "io_reads": p.io_reads,
            "io_writes": p.io_writes,
            "rss_before_kb": p.rss_before_kb,
            "rss_after_kb": p.rss_after_kb,
            "delta_rss_kb": p.delta_rss_kb,
            "artifact_count": p.artifact_count,
            "top_allocators": p.top_allocators,
        }
        for p in phases
    ]
