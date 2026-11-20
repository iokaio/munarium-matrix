# Publish the Server consumer profile

The [wire contract](../contract/README.md) and the Server consumer profile have
independent versions. The historical `0.1.0` wire bundle includes its README and
validator in its digest. Use the following commands from the Matrix root to
reproduce that bundle and export a separate profile for ClearView.

```sh
python contract/publish.py --out /tmp/matrix-wire
python contract/publish.py --verify /tmp/matrix-wire
python contract/publish.py --check /tmp/matrix-wire
python contract/publish.py --consumer-out /tmp/matrix-consumer.json
python contract/publish.py --consumer-check /tmp/matrix-consumer.json
```

The `--out` directory must be empty. The file for `--consumer-out` must be new.
`--verify` checks the lock and the exact file set. `--check` additionally compares
with a new cut and ignores only the recorded source commit in the lock. Install
`jsonschema` and run `python /tmp/matrix-wire/validate_examples.py` to validate
all eight schema-example pairings.

The export uses `format_version` 1, the wire version and digest, and the Matrix
revision verified against the released Server bundle. `profile_digest` is the
SHA-256 of the `profile` object serialized as UTF-8 JSON with ASCII escaping,
sorted keys and compact separators. `--consumer-check` compares the full output
bytes. Review and pin the publisher revision before accepting an export. The
source recorded in the original Server lock is `unknown`; the verified revision
in the new profile names a tree that reproduces all 17 locked files.

The `mmctl_matrix` profile names the ten v1.4 commands, fixed methods, relative
routes, operands and the two verification policies. The operator's configured
base URL remains the only authority. A consumer expands `{name}` within a path
segment and encodes `--limit` as a query value. Keep TLS, headers, response
formatting and usage handling in the bundled CLI. The profile contains no shell
commands or runtime downloads. See the [CLI crosswalk](user-guide.md#mxctl-and-mmctl-matrix)
for the output, auth and exit behavior.

```sh
python tools/check_mmctl_matrix.py /tmp/matrix-consumer.json --binary /path/to/mmctl
```

The CLI fixture listens only on loopback and checks requests, YAML bytes, status
handling, stdout and stderr. The interoperability workflow runs it against
source builds from Server main (or the dispatch-selected ref) and the pinned
v1.4.0 source. It also runs it against `/mmctl` in the published v1.4.0 image by
digest. Those checks establish CLI forwarding behavior. The same workflow runs
the Rust DTO and evidence-provider tests against the reproduced vectors and
exercises sealing, replay and reconciliation against real Server processes.
See the [transfer inventory](clearview-transfer.md) for remaining cutover checks.
