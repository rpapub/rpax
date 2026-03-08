"""Unit tests for src/rpax/versioning.py."""

import json

import pytest

from rpax.versioning import (
    BumpType,
    SemVer,
    bump,
    find_project_json,
    parse,
    read_project_version,
    write_project_version,
)


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,expected",
    [
        ("1.2.3", SemVer(1, 2, 3)),
        ("0.0.0", SemVer(0, 0, 0)),
        ("1.2.3-rc", SemVer(1, 2, 3, pre="rc")),
        ("1.2.3-rc.1", SemVer(1, 2, 3, pre="rc.1")),
        ("1.2.3-alpha.beta", SemVer(1, 2, 3, pre="alpha.beta")),
        ("1.2.3+build.1", SemVer(1, 2, 3, build="build.1")),
        ("1.2.3-rc.1+build", SemVer(1, 2, 3, pre="rc.1", build="build")),
    ],
)
def test_parse_valid(version: str, expected: SemVer) -> None:
    assert parse(version) == expected


@pytest.mark.parametrize(
    "version",
    ["", "1.2", "1.2.3.4", "abc", "1.2.x", "-1.2.3"],
)
def test_parse_invalid(version: str) -> None:
    with pytest.raises(ValueError, match="Invalid semver"):
        parse(version)


# ---------------------------------------------------------------------------
# bump()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,bump_type,pre_tag,expected",
    [
        # Clean → numeric bump
        ("1.2.3", BumpType.PATCH, "rc", "1.2.4"),
        ("1.2.3", BumpType.MINOR, "rc", "1.3.0"),
        ("1.2.3", BumpType.MAJOR, "rc", "2.0.0"),
        # Pre-release → pre-bump
        ("1.2.3", BumpType.PREPATCH, "rc", "1.2.4-rc"),
        ("1.2.3", BumpType.PREMINOR, "rc", "1.3.0-rc"),
        ("1.2.3", BumpType.PREMAJOR, "rc", "2.0.0-rc"),
        ("1.2.5", BumpType.PREMAJOR, "alpha", "2.0.0-alpha"),
        # prerelease on clean version → bump patch + bare tag
        ("1.2.3", BumpType.PRERELEASE, "rc", "1.2.4-rc"),
        # prerelease on matching bare tag → TAG.1
        ("1.2.3-rc", BumpType.PRERELEASE, "rc", "1.2.3-rc.1"),
        # finalize: patch/minor/major on pre-release → strip pre, no bump
        ("1.2.3-rc.1", BumpType.PATCH, "rc", "1.2.3"),
        # prerelease on TAG.N → TAG.(N+1)
        ("1.2.3-rc.1", BumpType.PRERELEASE, "rc", "1.2.3-rc.2"),
        # release → strip pre
        ("1.2.3-rc.1", BumpType.RELEASE, "rc", "1.2.3"),
        # tag mismatch → reset to bare new tag
        ("1.2.3-alpha", BumpType.PRERELEASE, "rc", "1.2.3-rc"),
        # build metadata stripped
        ("1.2.3+build.1", BumpType.PATCH, "rc", "1.2.4"),
    ],
)
def test_bump(version: str, bump_type: BumpType, pre_tag: str, expected: str) -> None:
    assert bump(version, bump_type, pre_tag) == expected


def test_bump_build_stripped_on_pre() -> None:
    assert bump("1.2.3-rc+build", BumpType.PRERELEASE, "rc") == "1.2.3-rc.1"


def test_bump_default_pre_tag() -> None:
    assert bump("1.2.3", BumpType.PRERELEASE) == "1.2.4-rc"


# ---------------------------------------------------------------------------
# find_project_json()
# ---------------------------------------------------------------------------


def test_find_project_json_directory(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text('{"name": "test"}', encoding="utf-8")
    assert find_project_json(tmp_path) == pj


def test_find_project_json_file_directly(tmp_path):
    pj = tmp_path / "my_project.json"
    pj.write_text('{"name": "test"}', encoding="utf-8")
    assert find_project_json(pj) == pj


def test_find_project_json_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="No project.json found"):
        find_project_json(tmp_path)


# ---------------------------------------------------------------------------
# read_project_version() / write_project_version()
# ---------------------------------------------------------------------------


def test_read_project_version(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps({"name": "x", "projectVersion": "1.2.3"}), encoding="utf-8")
    assert read_project_version(pj) == "1.2.3"


def test_write_project_version_roundtrip(tmp_path):
    data = {"name": "myProject", "projectVersion": "1.0.0", "extra": "keep me"}
    pj = tmp_path / "project.json"
    pj.write_text(json.dumps(data, indent=2), encoding="utf-8")

    write_project_version(pj, "1.0.1")

    result = json.loads(pj.read_text(encoding="utf-8"))
    assert result["projectVersion"] == "1.0.1"
    assert result["name"] == "myProject"
    assert result["extra"] == "keep me"


def test_write_project_version_preserves_key_order(tmp_path):
    pj = tmp_path / "project.json"
    pj.write_text('{"a": 1, "projectVersion": "1.0.0", "z": 99}\n', encoding="utf-8")

    write_project_version(pj, "2.0.0")

    text = pj.read_text(encoding="utf-8")
    # Ensure 'a' comes before 'z'
    assert text.index('"a"') < text.index('"z"')
    result = json.loads(text)
    assert result["projectVersion"] == "2.0.0"
