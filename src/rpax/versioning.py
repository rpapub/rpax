"""Semantic versioning utilities for UiPath project.json files."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


class BumpType(StrEnum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PREMAJOR = "premajor"
    PREMINOR = "preminor"
    PREPATCH = "prepatch"
    PRERELEASE = "prerelease"
    RELEASE = "release"


@dataclass
class SemVer:
    major: int
    minor: int
    patch: int
    pre: str | None = None
    build: str | None = None  # always stripped on bump


def parse(version: str) -> SemVer:
    """Parse a semver string into a SemVer dataclass. Raises ValueError on invalid input."""
    m = SEMVER_RE.match(version.strip())
    if not m:
        raise ValueError(f"Invalid semver: {version!r}")
    return SemVer(
        major=int(m.group("major")),
        minor=int(m.group("minor")),
        patch=int(m.group("patch")),
        pre=m.group("pre"),
        build=m.group("build"),
    )


def _format(sv: SemVer) -> str:
    """Serialize SemVer to string (build metadata always omitted)."""
    v = f"{sv.major}.{sv.minor}.{sv.patch}"
    if sv.pre:
        v += f"-{sv.pre}"
    return v


def _bump_prerelease(sv: SemVer, pre_tag: str) -> str:
    """Compute next prerelease version."""
    if sv.pre is None:
        # No existing pre-release: bump patch + bare tag
        return _format(SemVer(sv.major, sv.minor, sv.patch + 1, pre=pre_tag))

    pre = sv.pre

    # Bare matching tag → TAG.1
    if pre == pre_tag:
        return _format(SemVer(sv.major, sv.minor, sv.patch, pre=f"{pre_tag}.1"))

    # TAG.N matching → TAG.(N+1)
    prefix = pre_tag + "."
    if pre.startswith(prefix):
        rest = pre[len(prefix):]
        if rest.isdigit():
            return _format(SemVer(sv.major, sv.minor, sv.patch, pre=f"{pre_tag}.{int(rest) + 1}"))

    # Tag mismatch → reset to bare TAG
    return _format(SemVer(sv.major, sv.minor, sv.patch, pre=pre_tag))


def bump(version: str, bump_type: BumpType, pre_tag: str = "rc") -> str:
    """Return new version string after applying bump_type.

    For patch/minor/major on a pre-release version the pre-release is
    stripped (finalize) without a numeric increment.
    Build metadata is always stripped.
    """
    sv = parse(version)

    if bump_type == BumpType.MAJOR:
        if sv.pre is not None:
            return _format(SemVer(sv.major, sv.minor, sv.patch))
        return _format(SemVer(sv.major + 1, 0, 0))

    if bump_type == BumpType.MINOR:
        if sv.pre is not None:
            return _format(SemVer(sv.major, sv.minor, sv.patch))
        return _format(SemVer(sv.major, sv.minor + 1, 0))

    if bump_type == BumpType.PATCH:
        if sv.pre is not None:
            return _format(SemVer(sv.major, sv.minor, sv.patch))
        return _format(SemVer(sv.major, sv.minor, sv.patch + 1))

    if bump_type == BumpType.PREMAJOR:
        return _format(SemVer(sv.major + 1, 0, 0, pre=pre_tag))

    if bump_type == BumpType.PREMINOR:
        return _format(SemVer(sv.major, sv.minor + 1, 0, pre=pre_tag))

    if bump_type == BumpType.PREPATCH:
        return _format(SemVer(sv.major, sv.minor, sv.patch + 1, pre=pre_tag))

    if bump_type == BumpType.PRERELEASE:
        return _bump_prerelease(sv, pre_tag)

    if bump_type == BumpType.RELEASE:
        return _format(SemVer(sv.major, sv.minor, sv.patch))

    raise ValueError(f"Unknown bump type: {bump_type}")  # pragma: no cover


def find_project_json(path: Path) -> Path:
    """Resolve path to a project.json file.

    - If path is a file, return it directly.
    - If path is a directory, look for project.json inside it.
    - Raises FileNotFoundError if no project.json is found.
    """
    if path.is_file():
        return path
    candidate = path / "project.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"No project.json found in {path}")


def read_project_version(project_json: Path) -> str:
    """Read projectVersion from project.json. Raises KeyError if field absent."""
    data = json.loads(project_json.read_text(encoding="utf-8"))
    return data["projectVersion"]


def write_project_version(project_json: Path, new_version: str) -> None:
    """Write new_version back to projectVersion in project.json.

    Preserves field order and all other fields. Uses indent=2 (UiPath Studio default).
    """
    data = json.loads(project_json.read_text(encoding="utf-8"))
    data["projectVersion"] = new_version
    project_json.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
