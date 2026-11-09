#!/usr/bin/env python3
"""Dump Claude Code's own system prompt into providers/claude/system-prompt.md.

A plugin agent's body replaces Claude Code's system prompt, so the agents compose.py
generates carry it themselves, ahead of Crustify's text. This script captures it from a
real request: it runs `claude -p` once, in an empty directory, through a local proxy that
saves the request body (never its headers), and keeps the longest system block. The
`# Memory` section names one project's memory directory, so it is left out.

Rerun it when Claude Code is upgraded, then `compose.py build`. Standard library only.
"""
import http.server
import json
import re
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "system-prompt.md"
UPSTREAM = "https://api.anthropic.com"
bodies: list[bytes] = []


class Proxy(http.server.BaseHTTPRequestHandler):
    def _forward(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        if body and self.path.startswith("/v1/messages") and "count_tokens" not in self.path:
            bodies.append(body)
        req = urllib.request.Request(UPSTREAM + self.path, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length", "accept-encoding", "connection"):
                req.add_header(k, v)
        try:
            resp = urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=600)
        except urllib.error.HTTPError as e:
            resp = e
        self.send_response(resp.status if hasattr(resp, "status") else resp.code)
        for k, v in resp.headers.items():
            if k.lower() not in ("transfer-encoding", "connection", "content-length", "content-encoding"):
                self.send_header(k, v)
        self.send_header("Connection", "close")
        self.end_headers()
        while chunk := resp.read(8192):
            self.wfile.write(chunk)
            self.wfile.flush()

    do_GET = do_POST = _forward

    def log_message(self, *args):
        pass


def main() -> int:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {**__import__("os").environ,
           "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_address[1]}"}
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as empty:
        subprocess.run(["claude", "-p", "--model", "haiku", "Reply with the single word ok."],
                       cwd=empty, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                       check=True, timeout=300)
    server.shutdown()
    if not bodies:
        print("no request was captured", file=sys.stderr)
        return 1
    system = json.loads(bodies[0])["system"]
    blocks = [b["text"] for b in system] if isinstance(system, list) else [system]
    text = max(blocks, key=len).strip()
    text = re.sub(r"\n# Memory\n.*?(?=\n# )", "\n", text, flags=re.S)
    OUT.write_text(f"<!-- Claude Code's system prompt, as {version} sends it; "
                   f"dumped by dump-system-prompt.py -->\n\n{text}\n")
    print(f"{OUT}: {len(text)} characters, from {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
