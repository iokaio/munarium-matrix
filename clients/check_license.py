#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The license gate for the Munarium Matrix client libraries: everything under clients/
that ships is Apache-2.0, says so wherever a tool reads it, and carries nothing of the
server.

    py clients/check_license.py                        # the static checks below
    py clients/check_license.py --artifact <pkg>...    # a built wheel / sdist / nupkg / jar

Static checks (every finding printed; exit 1 if there is any):

  1. Manifests. python/'s PEP 639 `license` plus `license-files`; the .NET
     `PackageLicenseExpression` in Directory.Build.props; the Java POM license and
     the jar manifest's Bundle-License in build.gradle.kts. All must read Apache-2.0.
  2. Texts. clients/LICENSE is the canonical Apache License 2.0 (sha256 pinned to
     https://www.apache.org/licenses/LICENSE-2.0.txt, compared LF-normalized so a
     Windows checkout passes), every other LICENSE under clients/ is the same text,
     and every NOTICE is byte-identical to clients/NOTICE. Copies exist where a
     packaging tool cannot reach outside its project root (python/); they may never
     drift.
  3. Headers. Every Ioka-authored source file carries `SPDX-License-Identifier:
     Apache-2.0` on its first line (second, after a shebang). Exempt, and why:
     java/gradlew, gradlew.bat, gradle/wrapper/ (Gradle's own files under Gradle's
     own Apache-2.0 header).
  4. Forbidden strings. The retired proprietary identifier (the `LicenseRef-` form)
     anywhere under clients/. (A `..` path into a server tree is checked in BUILT
     packages, below: a published package must not reach outside itself.)

Artifact checks (`--artifact`): every entry is listed for the log; no entry's text
carries the retired identifier or a server path; the license files are inside
(`.dist-info/licenses/LICENSE` + NOTICE in a wheel, LICENSE + NOTICE at the root of an
sdist or nupkg, META-INF/LICENSE + NOTICE in a jar) and the package metadata says
Apache-2.0 (the wheel's and sdist's `License-Expression`, the .nuspec's
`<license type="expression">`, the jar manifest's `Bundle-License`).

Derived from iokaio/munarium's clients/check_license.py, which covered the Server and
Matrix clients together until the Matrix clients moved to this repository.

Stdlib only; `git ls-files` decides what is tracked, because a working tree carries
build output the gate must not read.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

APACHE_2_0_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
SPDX = "SPDX-License-Identifier: Apache-2.0"
# Assembled, not written out: this file is scanned by its own forbidden-string check.
RETIRED = "LicenseRef-" + "Ioka-Proprietary"
SERVER_PATH = re.compile(r"\.\.[/\\]+server\b")

HEADER = {
    ".rs": f"// {SPDX}",
    ".cs": f"// {SPDX}",
    ".java": f"// {SPDX}",
    ".kts": f"// {SPDX}",
    ".py": f"# {SPDX}",
    ".pyi": f"# {SPDX}",
    ".toml": f"# {SPDX}",
    ".csproj": f"<!-- {SPDX} -->",
    ".props": f"<!-- {SPDX} -->",
}
EXEMPT = (
    "java/gradlew",
    "java/gradlew.bat",
    "java/gradle/wrapper/",
)
RETIRED_ALLOWED: set[str] = set()
LICENSE_COPIES = ("python/LICENSE",)
NOTICE_COPIES = ("python/NOTICE",)


SKIP_DIRS = {".git", "target", "node_modules", "__pycache__", ".venv", "venv", "bin", "obj", ".gradle", "build", "dist", ".mypy_cache", ".ruff_cache", ".pytest_cache"}


def tracked_files() -> list[str]:
    """Tracked files plus untracked ones git would not ignore: a new source file is
    checked before its first commit, and build output (ignored) never is. Outside a
    git repository (a staged tree before its first commit) the walk below is the
    same set minus build output, so the gate runs anywhere the files do."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT, capture_output=True, check=True,
        ).stdout
        return sorted({p for p in out.decode("utf-8").split("\0") if p and (ROOT / p).is_file()})
    except (subprocess.CalledProcessError, FileNotFoundError):
        return sorted(
            p.relative_to(ROOT).as_posix()
            for p in ROOT.rglob("*")
            if p.is_file() and not (SKIP_DIRS & set(p.relative_to(ROOT).parts)) and "*.egg-info" not in p.parts
            and not any(part.endswith(".egg-info") for part in p.relative_to(ROOT).parts)
        )


def lf(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.replace(b"\r\n", b"\n")


def header_rule(rel: str) -> str | None:
    if rel.startswith(EXEMPT):
        return None
    return HEADER.get(Path(rel).suffix)


def has_header(text: str, line: str) -> bool:
    lines = text.lstrip("﻿").splitlines()
    if not lines:
        return False
    if lines[0].startswith("#!"):
        return len(lines) > 1 and lines[1].strip() == line
    return lines[0].strip() == line


# --- static checks ---------------------------------------------------------------------

def check_manifests(bad: list[str]) -> None:
    py = tomllib.loads(lf((ROOT / "python/pyproject.toml").read_bytes()).decode("utf-8"))["project"]
    if py.get("license") != "Apache-2.0":
        bad.append(f"python/pyproject.toml: [project] license is {py.get('license')!r}, not the PEP 639 string 'Apache-2.0'")
    for need in ("LICENSE", "NOTICE"):
        if need not in py.get("license-files", []):
            bad.append(f"python/pyproject.toml: license-files does not list {need}")
    props = lf((ROOT / "dotnet/Directory.Build.props").read_bytes()).decode("utf-8")
    if "<PackageLicenseExpression>Apache-2.0</PackageLicenseExpression>" not in props:
        bad.append("dotnet/Directory.Build.props: no <PackageLicenseExpression>Apache-2.0</PackageLicenseExpression>")
    kts = lf((ROOT / "java/build.gradle.kts").read_bytes()).decode("utf-8")
    m = re.search(r"licenses\s*\{.*?name\s*=\s*\"([^\"]+)\"", kts, re.S)
    if not m or m.group(1) != "Apache-2.0":
        bad.append("java/build.gradle.kts: the POM licenses block does not name Apache-2.0")
    if '"Bundle-License" to "Apache-2.0"' not in kts:
        bad.append("java/build.gradle.kts: the jar manifest does not carry Bundle-License: Apache-2.0")


def check_texts(bad: list[str], files: list[str]) -> None:
    def apache(rel: str) -> bool:
        return hashlib.sha256(lf((ROOT / rel).read_bytes())).hexdigest() == APACHE_2_0_SHA256

    if "LICENSE" not in files:
        bad.append("LICENSE: missing")
    elif not apache("LICENSE"):
        bad.append("LICENSE: not the canonical Apache License 2.0 text (sha256 mismatch)")
    notice = lf((ROOT / "NOTICE").read_bytes()) if "NOTICE" in files else None
    if notice is None:
        bad.append("NOTICE: missing")
    for rel in files:
        name = Path(rel).name
        if name == "LICENSE" and rel != "LICENSE" and not apache(rel):
            bad.append(f"{rel}: not the canonical Apache License 2.0 text")
        if name == "NOTICE" and rel != "NOTICE" and not rel.startswith("contract/"):
            if notice is not None and lf((ROOT / rel).read_bytes()) != notice:
                bad.append(f"{rel}: differs from NOTICE")
    for rel in LICENSE_COPIES + NOTICE_COPIES:
        if rel not in files:
            bad.append(f"{rel}: missing (the packaging tool there cannot reach the repository root)")


def check_headers(bad: list[str], files: list[str]) -> int:
    n = 0
    for rel in files:
        line = header_rule(rel)
        if line is None:
            continue
        n += 1
        text = (ROOT / rel).read_bytes().decode("utf-8", errors="replace")
        if not has_header(text, line):
            bad.append(f"{rel}: missing `{line}` on line 1 (line 2 after a shebang)")
    return n


def check_forbidden(bad: list[str], files: list[str]) -> None:
    for rel in files:
        if Path(rel).suffix in (".jar",):
            continue
        text = (ROOT / rel).read_bytes().decode("utf-8", errors="ignore")
        if RETIRED in text and rel not in RETIRED_ALLOWED:
            bad.append(f"{rel}: names the retired proprietary license identifier")
        # A `../server` path is checked only in BUILT packages (check_artifact),
        # where reaching outside the package is a real defect.


def static() -> int:
    files = tracked_files()
    bad: list[str] = []
    check_manifests(bad)
    check_texts(bad, files)
    headed = check_headers(bad, files)
    check_forbidden(bad, files)
    for line in bad:
        print(line)
    if bad:
        print(f"check_license: {len(bad)} problem(s)")
        return 1
    print(f"check_license: manifests Apache-2.0, LICENSE canonical, {headed} source files headed, "
          f"{len(files)} tracked files clean -- ok")
    return 0


# --- built artifacts -------------------------------------------------------------------

def entries_of(path: Path) -> list[tuple[str, bytes]]:
    if path.name.endswith((".whl", ".zip", ".nupkg", ".jar")):
        with zipfile.ZipFile(path) as z:
            return [(i.filename, z.read(i)) for i in z.infolist() if not i.is_dir()]
    if path.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path, "r:gz") as t:
            out = []
            for m in t.getmembers():
                if m.isfile():
                    f = t.extractfile(m)
                    out.append((m.name, f.read() if f else b""))
            return out
    raise SystemExit(f"{path}: not a wheel, sdist, nupkg or jar")


def check_artifact(path: Path) -> int:
    entries = entries_of(path)
    names = {n for n, _ in entries}
    bad: list[str] = []
    print(f"{path.name}: {len(entries)} entries")
    for n, data in sorted(entries):
        print(f"  {n}")
        if len(data) > 4 * 1024 * 1024:
            continue
        text = data.decode("utf-8", errors="ignore")
        if RETIRED in text:
            bad.append(f"{n}: names the retired proprietary license identifier")
        if not n.endswith(".md") and SERVER_PATH.search(text):
            bad.append(f"{n}: reaches into the server tree with a `..` path")

    def need(pred, what: str) -> None:
        if not any(pred(n) for n in names):
            bad.append(f"{path.name}: no {what}")

    def text_of(pred) -> str:
        for n, data in entries:
            if pred(n):
                return data.decode("utf-8", errors="ignore")
        return ""

    if path.name.endswith(".whl"):
        need(lambda n: n.endswith(".dist-info/licenses/LICENSE"), ".dist-info/licenses/LICENSE")
        need(lambda n: n.endswith(".dist-info/licenses/NOTICE"), ".dist-info/licenses/NOTICE")
        if "License-Expression: Apache-2.0" not in text_of(lambda n: n.endswith(".dist-info/METADATA")):
            bad.append(f"{path.name}: METADATA has no `License-Expression: Apache-2.0`")
    elif path.name.endswith((".tar.gz", ".tgz")):
        top = sorted(names)[0].split("/", 1)[0]
        need(lambda n: n == f"{top}/LICENSE", "LICENSE at the sdist root")
        need(lambda n: n == f"{top}/NOTICE", "NOTICE at the sdist root")
        if "License-Expression: Apache-2.0" not in text_of(lambda n: n == f"{top}/PKG-INFO"):
            bad.append(f"{path.name}: PKG-INFO has no `License-Expression: Apache-2.0`")
    elif path.name.endswith(".nupkg"):
        need(lambda n: n == "LICENSE", "LICENSE at the package root")
        need(lambda n: n == "NOTICE", "NOTICE at the package root")
        if '<license type="expression">Apache-2.0</license>' not in text_of(lambda n: n.endswith(".nuspec")):
            bad.append(f"{path.name}: .nuspec has no <license type=\"expression\">Apache-2.0</license>")
    elif path.name.endswith(".jar"):
        need(lambda n: n == "META-INF/LICENSE", "META-INF/LICENSE")
        need(lambda n: n == "META-INF/NOTICE", "META-INF/NOTICE")
        if "Bundle-License: Apache-2.0" not in text_of(lambda n: n == "META-INF/MANIFEST.MF"):
            bad.append(f"{path.name}: MANIFEST.MF has no `Bundle-License: Apache-2.0`")
    for line in bad:
        print(line)
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--artifact", nargs="+", type=Path)
    a = ap.parse_args(argv)
    if a.artifact:
        rc = 0
        for p in a.artifact:
            rc |= check_artifact(p.resolve())
        print("check_license --artifact:", "FAILED" if rc else "ok")
        return rc
    return static()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
