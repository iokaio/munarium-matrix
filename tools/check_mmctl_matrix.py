#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare the exported Matrix command profile with a built mmctl binary."""

import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Thread
import uuid


def check(binary, image, commands):
    replies = deque()
    requests = deque()

    class Peer(BaseHTTPRequestHandler):
        def reply(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            requests.append((self.command, self.path, self.headers, body))
            status, response = replies.popleft() if replies else (500, {})
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        do_GET = do_POST = reply

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Peer) as peer:
        thread = Thread(target=peer.serve_forever)
        thread.start()
        try:
            run_cases(binary, image, commands, peer.server_port, replies, requests)
        finally:
            peer.shutdown()
            thread.join()


def run_cases(binary, image, commands, port, replies, requests):
    env = {
        **os.environ,
        "MUNARIUMCTL_MATRIX_URL": f"http://127.0.0.1:{port}",
        "MUNARIUMCTL_MATRIX_TOKEN": "fixture-token",
        "MUNARIUMCTL_UID": "matrix-fixture",
        "NO_PROXY": "127.0.0.1",
    }
    request_ids = set()

    def run(args, expected=(), results=(), *, code=0, output=None, error="", yaml=b""):
        replies.extend(results)
        proc = subprocess.run([*launcher, "matrix", *args], env=env, capture_output=True,
                              text=True, timeout=30, check=False)
        assert proc.returncode == code, (args, proc.returncode, proc.stderr)
        stdout = "" if output is None else json.dumps(output, indent=2, sort_keys=True) + "\n"
        assert proc.stdout == stdout, (args, proc.stdout, stdout)
        assert proc.stderr == error, (args, proc.stderr, error)
        actual = list(requests)
        requests.clear()
        assert not replies, (args, "expected replies remained", list(replies))
        assert [(method, path) for method, path, _, _ in actual] == list(expected), (args, actual)
        for _, _, headers, body in actual:
            token = env.get("MUNARIUMCTL_MATRIX_TOKEN")
            assert headers.get("Authorization") == (f"Bearer {token}" if token else None)
            assert headers.get("X-Munarium-Uid") == env.get("MUNARIUMCTL_UID", "mmctl")
            request_id = uuid.UUID(headers["X-Munarium-Request-Id"])
            assert request_id.version == 4 and request_id not in request_ids
            request_ids.add(request_id)
            assert headers.get("Content-Type") == ("text/yaml" if yaml else None)
            assert body == yaml

    assert set(commands) == {
        "apply", "introspect", "journal", "probe", "reconcile", "sync", "validate",
        "verify", "verify-view", "version",
    }
    sent_yaml = b"kind: fixture\n"
    success = {"answer": [1, "fixture"]}
    usage = (
        "mmctl matrix: usage: mmctl matrix version | apply -f <yaml> | validate -f <yaml> | "
        "introspect <source> | probe <source> | verify <contract> | verify-view <view> | "
        "sync <source> | reconcile <mapping> | journal [--limit N]\n"
    )
    with tempfile.TemporaryDirectory() as directory:
        asset = Path(directory) / "asset.yaml"
        asset.write_bytes(sent_yaml)
        asset_arg = str(asset)
        launcher = [binary]
        if image:
            asset.chmod(0o644)
            asset_arg = "/matrix-fixture.yaml"
            launcher = [
                "docker", "run", "--rm", "--pull=never", "--network=host", "--entrypoint=/mmctl",
                "--env", "MUNARIUMCTL_MATRIX_URL", "--env", "MUNARIUMCTL_MATRIX_TOKEN",
                "--env", "MUNARIUMCTL_UID", "--env", "NO_PROXY",
                "--mount", f"type=bind,src={asset},dst={asset_arg},readonly", image,
            ]
        for verb, spec in commands.items():
            path = spec["path"].format(name="fixture@2")
            args, body = [verb], b""
            if "operand" in spec:
                args.append("fixture@2")
                run([verb], code=1, error=f"mmctl matrix: usage: mmctl matrix {verb} <{spec['operand']}>\n")
            if "yaml_flag" in spec:
                args.extend([spec["yaml_flag"], asset_arg])
                body = sent_yaml
                run([verb], code=1, error="mmctl matrix: usage: -f <asset.yaml>\n")
            if "default_limit" in spec:
                run([verb, spec["limit_flag"], "7"], [(spec["method"], f"{path}?limit=7")],
                    [(200, success)], output=success)
                path += f"?limit={spec['default_limit']}"
            run(args, [(spec["method"], path)], [(200, success)], output=success, yaml=body)

        view = commands["verify-view"]
        assert view["verification"] == "failed"
        view_path = (view["method"], view["path"].format(name="v"))
        data_path = (view["method"], view["fallback_404"].format(name="v"))
        failed = {"failed": 1}
        run(["verify-view", "v"], [view_path, data_path], [(404, {}), (200, failed)],
            code=3, output=failed)
        run(["verify-view", "v"], [view_path], [(403, {"detail": "denied"})],
            code=1, error="mmctl matrix: 403 Forbidden: denied\n")

        verify = commands["verify"]
        assert verify["verification"] == "failed_or_questions"
        for result in (failed, {"failed": 0, "questions": [{"ok": False}]}):
            run(["verify", "v"], [(verify["method"], verify["path"].format(name="v"))],
                [(200, result)], code=3, output=result)

        refusal = {"detail": "invalid asset", "refusal": [
            {"code": "invalid_type", "path": "spec", "message": "expected object"}
        ]}
        run(["validate", "-f", asset_arg], [("POST", "/v1/assets/validate")], [(422, refusal)],
            code=1, error="  invalid_type  spec  expected object\nmmctl matrix: 422 Unprocessable Entity: invalid asset\n",
            yaml=sent_yaml)

        run([], code=1, error=usage)
        run(["unknown"], code=1, error=usage)
        del env["MUNARIUMCTL_MATRIX_TOKEN"], env["MUNARIUMCTL_UID"]
        run(["version"], [("GET", "/version")], [(200, success)], output=success)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--binary", type=Path)
    source.add_argument("--image", help="locally available Server image, on a Linux Docker host")
    args = parser.parse_args()
    profile = json.loads(args.profile.read_bytes())["profile"]
    binary = str(args.binary.resolve(strict=True)) if args.binary else None
    check(binary, args.image, profile["mmctl_matrix"]["commands"])
    print("mmctl matrix: all ten verbs, requests, outputs and exit cases passed")
