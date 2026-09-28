#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The mechanical ground rules, in one place because two copies disagreed.

Ground rules 1 and 3 (`00-overview.md` §8) are checked by grepping a
`cargo tree` and the migration files. Until 2026-08-30 they were checked
TWICE — once in `test.ps1` for the laptop and once in `matrix-ci.yml` for CI —
with three differences between the copies, and one of them made CI red for
three pushes while the laptop stayed green:

  * `cargo tree` defaults to the HOST target. `openssl-probe` is
    `cfg(unix)`, so a Windows laptop never saw it and Ubuntu always did.
  * the openssl rule matched the PREFIX `openssl`, so `openssl-probe` —
    which is `rustls-native-certs`' CA-path finder, links nothing, and is in
    the graph BECAUSE the tree is rustls-only — read as "openssl entered the
    graph".
  * the migration rule banned a retype on the laptop and not in CI.

So: one implementation, one target, one answer everywhere. The target is the
one that SHIPS (`x86_64-unknown-linux-musl`, the Dockerfile's), because the
graph worth ruling on is the deployed graph, and pinning it is what stops a
laptop and a runner from disagreeing again.

Exit 1 on any violation, naming it. Stdlib only.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The graph that ships. Not the host's: see the docstring.
TARGET = "x86_64-unknown-linux-musl"

# Ground rule 1: matrix/ never depends on a server/ crate. The official Rust
# client path-depends on three of them, so this also catches "just use the
# official client" (questions.md Q7).
SERVER_CRATES = [
    "munarium-core",
    "munarium-api-types",
    "munarium-proto",
    "munarium-shapes",
    "munarium-runbooks",
]

# The kernel stays pure — no runtime, no driver — which is what keeps evidence
# identity testable in milliseconds.
CORE_BANNED = ["sqlx", "reqwest", "axum", "tokio", "object_store"]

# Munarium Matrix Enterprise. These adapters reach analytics platforms an
# enterprise buys and administers separately; they are a separate product and
# must not appear in the graph a Munarium Matrix CORE build ships. The check is
# run against the featureless build, which is what the core tree compiles: with
# `enterprise-adapters` on -- the default in the research workspace -- they are
# expected, and this rule is skipped rather than made to lie.
ENTERPRISE_ADAPTERS = [
    "munarium-matrix-adapter-databricks",
    "munarium-matrix-adapter-snowflake",
    "munarium-matrix-adapter-bigquery",
    "munarium-matrix-adapter-cube",
    "munarium-matrix-adapter-dbt",
]

# Ground rule 3: rustls only. Named exactly, never by prefix.
TLS_BANNED = [
    "openssl",
    "openssl-sys",
    "openssl-macros",
    "native-tls",
    "hyper-tls",
    "tokio-native-tls",
    "tokio-openssl",
]

# In the graph BECAUSE the tree is rustls-only. `openssl-probe` reads the
# platform's CA bundle path for `rustls-native-certs`; it links no C and
# depends on nothing. Listing it here is the difference between a rule and a
# prefix match that cannot tell the two apart.
TLS_ALLOWED = {"openssl-probe": "rustls-native-certs' CA-path finder; links nothing"}


def tree(args: list[str]) -> list[str]:
    out = subprocess.run(
        ["cargo", "tree", "--edges", "normal", "--prefix", "none", "--target", TARGET, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        print(out.stdout)
        print(out.stderr, file=sys.stderr)
        sys.exit(f"cargo tree failed: {' '.join(args)}")
    # "name v1.2.3 (path)" -> "name"
    return sorted({line.split()[0] for line in out.stdout.splitlines() if line.strip()})


def main() -> int:
    failures: list[str] = []

    workspace = tree(["--workspace"])
    core = tree(["-p", "munarium-matrix-core"])
    # What a core build actually links: the server crate with its default
    # features off. `cargo tree` resolves features per invocation, so this is a
    # second call rather than a filter over the first.
    core_build = tree(["-p", "munarium-matrix-server", "--no-default-features"])

    for crate in SERVER_CRATES:
        if crate in workspace:
            failures.append(f"matrix/ must not depend on the server crate '{crate}' (ground rule 1)")

    for crate in CORE_BANNED:
        if crate in core:
            failures.append(f"munarium-matrix-core must not depend on {crate}")

    for crate in TLS_BANNED:
        if crate in workspace:
            failures.append(f"{crate} entered the graph; rustls only (ground rule 3)")

    # The open/Enterprise line, made mechanical. A core build that links one of
    # these is not a core build, and the failure names which one so the fix is
    # obvious: an `#[cfg(feature = "enterprise-adapters")]` was missed.
    for crate in ENTERPRISE_ADAPTERS:
        if crate in core_build:
            failures.append(
                f"{crate} is in the CORE build graph; it is Munarium Matrix Enterprise. "
                "Check for a missing #[cfg(feature = \"enterprise-adapters\")]"
            )

    # A migration that drops, retypes or renames is how an operator loses data
    # during a rolling deploy. Crude on purpose: a rule that cannot be argued
    # with.
    bad_sql = re.compile(
        r"\b(drop\s+table|drop\s+column|alter\s+column\s+\w+\s+type|rename\s+to)\b",
        re.IGNORECASE,
    )
    for path in sorted((ROOT / "src/munarium-matrix-store/migrations").glob("*.sql")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if bad_sql.search(line):
                failures.append(f"non-additive migration: {path.name}:{n} {line.strip()}")

    for f in failures:
        print(f"::error::{f}" if "CI" in __import__("os").environ else f"FAIL: {f}")
    if failures:
        return 1

    allowed = ", ".join(f"{k} ({v})" for k, v in TLS_ALLOWED.items() if k in workspace)
    print(
        f"boundaries: {len(workspace)} crates in the shipping graph ({TARGET}): "
        f"no server crate, core is pure, rustls only, migrations additive; "
        f"the core build ({len(core_build)} crates) carries no Enterprise adapter"
        + (f"; allowed beside rustls: {allowed}" if allowed else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
