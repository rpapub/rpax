"""Unit tests for BayPortrait (rpax view command)."""

from pathlib import Path

import pytest

from rpax.explain.portrait import BayPortrait, _density_char, _mini_bar

# ---------------------------------------------------------------------------
# Helper to create a portrait with injected data (no disk I/O)
# ---------------------------------------------------------------------------

def _make_portrait(
    workflows: list | None = None,
    call_graph_metrics: dict | None = None,
    call_graph_workflows: dict | None = None,
    metrics: list | None = None,
) -> BayPortrait:
    portrait = BayPortrait(Path("/fake"))
    portrait._manifest = {
        "projectName": "TestProject",
        "projectType": "process",
        "projectVersion": "1.0.0",
        "generatedAt": "2026-01-15T12:00:00Z",
        "parseErrors": [],
    }
    portrait._workflows_index = {"workflows": workflows or []}
    portrait._call_graph = {
        "metrics": call_graph_metrics or {},
        "workflows": call_graph_workflows or {},
    }
    portrait._metrics = metrics or []
    return portrait


# ---------------------------------------------------------------------------
# _density_char
# ---------------------------------------------------------------------------

def test_density_char_zero():
    assert _density_char(0) == "·"


def test_density_char_sparse():
    assert _density_char(1) == "░"
    assert _density_char(3) == "░"


def test_density_char_medium():
    assert _density_char(4) == "▒"
    assert _density_char(8) == "▒"


def test_density_char_dense():
    assert _density_char(9) == "▓"
    assert _density_char(20) == "▓"


def test_density_char_full():
    assert _density_char(21) == "█"
    assert _density_char(999) == "█"


# ---------------------------------------------------------------------------
# _mini_bar
# ---------------------------------------------------------------------------

def test_mini_bar_zero():
    bar = _mini_bar(0.0, width=10)
    assert bar == "░" * 10
    assert len(bar) == 10


def test_mini_bar_full():
    bar = _mini_bar(1.0, width=10)
    assert bar == "█" * 10


def test_mini_bar_half():
    bar = _mini_bar(0.5, width=10)
    assert len(bar) == 10
    assert "█" in bar
    assert "░" in bar


def test_mini_bar_clamps_ratio():
    assert _mini_bar(2.0, 8) == "█" * 8
    assert _mini_bar(-1.0, 8) == "░" * 8


def test_mini_bar_width():
    for w in [4, 6, 8, 12]:
        assert len(_mini_bar(0.5, w)) == w


# ---------------------------------------------------------------------------
# _signature_chars
# ---------------------------------------------------------------------------

def test_signature_chars_empty():
    portrait = _make_portrait(workflows=[])
    result = portrait._signature_chars()
    assert result == []


def test_signature_chars_single():
    portrait = _make_portrait(workflows=[{"totalActivities": 5, "relativePath": "A.xaml"}])
    result = portrait._signature_chars()
    assert result == [5]


def test_signature_chars_sorted_ascending():
    wfs = [
        {"totalActivities": 15, "relativePath": "A.xaml"},
        {"totalActivities": 2, "relativePath": "B.xaml"},
        {"totalActivities": 8, "relativePath": "C.xaml"},
    ]
    portrait = _make_portrait(workflows=wfs)
    result = portrait._signature_chars()
    assert result == [2, 8, 15]


def test_signature_chars_zero_activities():
    wfs = [
        {"totalActivities": 0, "relativePath": "Empty.xaml"},
        {"totalActivities": None, "relativePath": "None.xaml"},
    ]
    portrait = _make_portrait(workflows=wfs)
    result = portrait._signature_chars()
    assert result == [0, 0]


# ---------------------------------------------------------------------------
# _style_dimensions — when metrics dir is empty
# ---------------------------------------------------------------------------

def test_style_dimensions_empty_metrics():
    portrait = _make_portrait(metrics=[])
    dims = portrait._style_dimensions()
    assert set(dims.keys()) == {"orchestration", "deep", "documented", "defensive"}
    assert dims["orchestration"] == 0.5   # default when no data
    assert dims["deep"] == 0.0
    assert dims["documented"] == 0.0
    assert dims["defensive"] == 0.0


def test_style_dimensions_all_invoke():
    portrait = _make_portrait(
        metrics=[{"invokeCount": 10, "selectorCount": 0, "tryCatchCount": 0,
                  "annotatedActivityCount": 0, "totalNodes": 10}],
        call_graph_metrics={"max_call_depth": 4},
        workflows=[{"totalActivities": 5, "relativePath": "A.xaml"}],
    )
    dims = portrait._style_dimensions()
    assert dims["orchestration"] == 1.0


def test_style_dimensions_all_selector():
    portrait = _make_portrait(
        metrics=[{"invokeCount": 0, "selectorCount": 10, "tryCatchCount": 0,
                  "annotatedActivityCount": 0, "totalNodes": 10}],
        call_graph_metrics={"max_call_depth": 0},
        workflows=[{"totalActivities": 5, "relativePath": "A.xaml"}],
    )
    dims = portrait._style_dimensions()
    assert dims["orchestration"] == 0.0


def test_style_dimensions_documented():
    portrait = _make_portrait(
        metrics=[{"invokeCount": 0, "selectorCount": 0, "tryCatchCount": 0,
                  "annotatedActivityCount": 5, "totalNodes": 10}],
        call_graph_metrics={"max_call_depth": 0},
    )
    dims = portrait._style_dimensions()
    assert dims["documented"] == pytest.approx(0.5)


def test_style_dimensions_defensive_clamped():
    portrait = _make_portrait(
        metrics=[{"invokeCount": 0, "selectorCount": 0, "tryCatchCount": 100,
                  "annotatedActivityCount": 0, "totalNodes": 100}],
        call_graph_metrics={"max_call_depth": 0},
        workflows=[{"totalActivities": 1, "relativePath": "A.xaml"}],
    )
    dims = portrait._style_dimensions()
    assert dims["defensive"] == 1.0


def test_style_dimensions_deep_clamped():
    portrait = _make_portrait(
        call_graph_metrics={"max_call_depth": 20},
    )
    dims = portrait._style_dimensions()
    assert dims["deep"] == 1.0


# ---------------------------------------------------------------------------
# _folder_counts
# ---------------------------------------------------------------------------

def test_folder_counts_flat_project():
    """Workflows with no subdirectory get bucketed under '(root)'."""
    wfs = [
        {"relativePath": "Main.xaml"},
        {"relativePath": "Other.xaml"},
    ]
    portrait = _make_portrait(workflows=wfs)
    counts = portrait._folder_counts()
    assert counts == {"(root)": 2}


def test_folder_counts_nested_project():
    wfs = [
        {"relativePath": "Framework/Init.xaml"},
        {"relativePath": "Framework/Close.xaml"},
        {"relativePath": "Process/Main.xaml"},
    ]
    portrait = _make_portrait(workflows=wfs)
    counts = portrait._folder_counts()
    assert counts == {"Framework": 2, "Process": 1}


def test_folder_counts_deeply_nested():
    wfs = [
        {"relativePath": "Framework/Sub/Deep/Workflow.xaml"},
    ]
    portrait = _make_portrait(workflows=wfs)
    counts = portrait._folder_counts()
    assert counts == {"Framework": 1}


def test_folder_counts_mixed_separators():
    """Windows-style backslashes should be normalised."""
    wfs = [
        {"relativePath": "Framework\\Init.xaml"},
        {"relativePath": "Framework/Close.xaml"},
    ]
    portrait = _make_portrait(workflows=wfs)
    counts = portrait._folder_counts()
    assert counts == {"Framework": 2}


def test_folder_counts_empty():
    portrait = _make_portrait(workflows=[])
    assert portrait._folder_counts() == {}


# ---------------------------------------------------------------------------
# render — smoke test (no crash, produces output)
# ---------------------------------------------------------------------------

def test_render_smoke(capsys):
    """Render should complete without error even with minimal data."""
    from io import StringIO

    from rich.console import Console as RichConsole

    portrait = _make_portrait(
        workflows=[
            {"totalActivities": 5, "relativePath": "Framework/Init.xaml"},
            {"totalActivities": 0, "relativePath": "Process/Main.xaml"},
        ],
        call_graph_metrics={
            "total_workflows": 2, "total_dependencies": 1,
            "entry_points": 1, "orphaned_workflows": 0,
            "max_call_depth": 3,
        },
        metrics=[{"invokeCount": 3, "selectorCount": 1, "tryCatchCount": 1,
                   "annotatedActivityCount": 2, "totalNodes": 10}],
    )

    buf = StringIO()
    rich_console = RichConsole(file=buf, width=80, highlight=False)
    portrait.render(rich_console, width=80)
    output = buf.getvalue()

    assert "TestProject" in output
    assert "DEPTH" in output
    assert "FOLDERS" in output
    assert "SIGNATURE" in output
    assert "STYLE" in output
    # Border chars
    assert "┌" in output
    assert "└" in output
