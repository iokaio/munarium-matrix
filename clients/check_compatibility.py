#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""compatibility.json must match what each Matrix client manifest actually declares
-- otherwise the compatibility record documents a release that cannot happen.
Read, never regenerated: the manifests are the source of truth; this script is
the drift check between them and the record a human wrote by hand at release
time.

    py clients/check_compatibility.py

Four things are checked per client, not one:

  * `version`   -- against the manifest's version
  * `package`   -- against the manifest's package name / id / coordinate
  * `registry`  -- against the registry that manifest can target
  * publishable -- the manifest actually carries what the named registry
                   requires (a maven-publish publication with url/licenses/
                   developers/scm for Maven Central)

Checking only `version` is how compatibility.json once promised a PyPI package
called `munarium-matrix-client` while the pyproject declared `munarium-matrix`,
and a Maven Central release from a build file whose own first comment said it
was never published to a registry. Both passed.

The record's `target_matrix` must also be the Matrix this checkout builds (the
workspace version in ../Cargo.toml), `supported_matrix` must lead with its
minor, and the clients' target constants must name it.

Derived from iokaio/munarium's clients/check_compatibility.py, which covered the
Server and Matrix clients together until the Matrix clients moved here.

Exit 1 on any mismatch or missing entry. Stdlib only (the Directory.Build.props
read is a regex over XML text, not a full parser -- sufficient for one
<Version> element).
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def python_version() -> str:
    d = tomllib.loads((ROOT / "python/pyproject.toml").read_text(encoding="utf-8"))
    return d["project"]["version"]


def dotnet_version() -> str:
    text = (ROOT / "dotnet/Directory.Build.props").read_text(encoding="utf-8")
    m = re.search(r"<Version>([^<]+)</Version>", text)
    if not m:
        raise SystemExit("dotnet/Directory.Build.props: no <Version> element found")
    return m.group(1)


def java_version() -> str:
    text = (ROOT / "java/build.gradle.kts").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit('java/build.gradle.kts: no top-level version = "..." found')
    return m.group(1)


# --------------------------------------------------------------- package ids


def python_package() -> str:
    d = tomllib.loads((ROOT / "python/pyproject.toml").read_text(encoding="utf-8"))
    return d["project"]["name"]


def dotnet_package() -> str:
    """NuGet id: an explicit <PackageId>, else the .csproj file name."""
    props = ROOT / "dotnet/Directory.Build.props"
    m = re.search(r"<PackageId>([^<]+)</PackageId>", props.read_text(encoding="utf-8"))
    if m:
        return m.group(1)
    projects = sorted(props.parent.glob("src/*/*.csproj"))
    if not projects:
        raise SystemExit(f"{props}: no <PackageId> and no project matching src/*/*.csproj")
    return projects[0].stem


def java_package() -> str:
    path = ROOT / "java/build.gradle.kts"
    text = path.read_text(encoding="utf-8")
    group = re.search(r'^group\s*=\s*"([^"]+)"', text, re.M)
    name = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.M)
    if not group or not name:
        raise SystemExit(f"{path}: need a top-level group and a POM name to form a coordinate")
    return f"{group.group(1)}:{name.group(1)}"


# ------------------------------------------------------------- publishability

# What Maven Central requires of a manifest before a release can even be
# attempted. Each entry is (needle, why) checked against the build file text.
MAVEN_CENTRAL_REQUIRES = [
    ("`maven-publish`", "the maven-publish plugin"),
    ("MavenPublication", "a publication"),
    ("licenses {", "a <licenses> block"),
    ("developers {", "a <developers> block"),
    ("scm {", "an <scm> block"),
    ("url =", "a project url"),
    ("withSourcesJar()", "a -sources jar"),
    ("withJavadocJar()", "a -javadoc jar"),
]

REGISTRY = {"matrix-python": "PyPI", "matrix-dotnet": "NuGet", "matrix-java": "Maven Central"}


def registry_problems(lang: str, entry: dict) -> list[str]:
    """Can this manifest target the registry compatibility.json names?"""
    registry = entry.get("registry")
    if registry is None:
        return [f"{lang}: no registry named in compatibility.json"]
    if registry != REGISTRY[lang]:
        return [f"{lang}: registry {registry!r} is not this ecosystem's ({REGISTRY[lang]!r})"]
    if registry != "Maven Central":
        return []
    path = ROOT / "java/build.gradle.kts"
    text = path.read_text(encoding="utf-8")
    missing = [why for needle, why in MAVEN_CENTRAL_REQUIRES if needle not in text]
    if missing:
        return [f"{lang}: compatibility.json promises Maven Central but "
                f"{path.name} is missing {', '.join(missing)}"]
    return []


READERS = {
    "matrix-python": (python_version, python_package),
    "matrix-dotnet": (dotnet_version, dotnet_package),
    "matrix-java": (java_version, java_package),
}


def matrix_workspace_version() -> str:
    d = tomllib.loads((ROOT.parent / "Cargo.toml").read_text(encoding="utf-8"))
    return d["workspace"]["package"]["version"]


# The Matrix release each client says it targets. The Python and Java clients
# read `/version` and carry no target constant.
TARGET_CONSTANTS = {
    "matrix-dotnet": ("dotnet/src/Ioka.Munarium.Matrix.Client/MatrixClient.cs", r'TargetVersion = "([^"]+)"'),
}


def matrix_target_problems(record: dict) -> list[str]:
    target = record.get("target_matrix", "")
    if not isinstance(target, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", target):
        return ["target_matrix must name an exact Matrix release (major.minor.patch)"]
    bad = []
    workspace = matrix_workspace_version()
    if target != workspace:
        bad.append(f"target_matrix is {target} but this checkout builds Matrix {workspace} (../Cargo.toml)")
    minor = ".".join(target.split(".")[:2])
    for lang, entry in record["clients"].items():
        ranges = entry.get("supported_matrix")
        if entry.get("speaks_to") != "matrix" or "supported_server" in entry:
            bad.append(f"{lang}: a Matrix client speaks to Matrix and declares no Server range")
        if not ranges or ranges[0] != minor:
            bad.append(f"{lang}: supported_matrix must lead with the target minor {minor}")
    for lang, (path, pattern) in TARGET_CONSTANTS.items():
        source = ROOT / path
        found = re.findall(pattern, source.read_text(encoding="utf-8")) if source.is_file() else []
        if found != [target]:
            bad.append(f"{lang}: target Matrix constant in {path} must equal {target}")
    return bad


def main() -> int:
    record = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
    bad: list[str] = matrix_target_problems(record)

    # Every entry in the record needs a reader, and every reader an entry --
    # otherwise a client can be added to one and forgotten in the other.
    for lang in record["clients"]:
        if lang not in READERS:
            bad.append(f"{lang}: in compatibility.json but this script cannot read its manifest")

    for lang, (read_version, read_package) in READERS.items():
        entry = record["clients"].get(lang)
        if entry is None:
            bad.append(f"{lang}: no entry in compatibility.json")
            continue

        actual = read_version()
        if entry["version"] != actual:
            bad.append(
                f"{lang}: compatibility.json says version {entry['version']!r}, "
                f"the manifest says {actual!r}"
            )

        declared = read_package()
        if entry.get("package") != declared:
            bad.append(
                f"{lang}: compatibility.json says package {entry.get('package')!r}, "
                f"the manifest declares {declared!r}"
            )

        bad.extend(registry_problems(lang, entry))

    if bad:
        for line in bad:
            print(line)
        print(f"check_compatibility: {len(bad)} problem(s) -- "
              "fix the manifest or the record, whichever is wrong")
        return 1
    print(f"check_compatibility: {len(READERS)} client(s) -- version, package id, "
          "registry, publishability and Matrix target/ranges agree with compatibility.json -- ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
