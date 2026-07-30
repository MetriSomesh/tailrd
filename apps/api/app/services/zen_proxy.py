#!/usr/bin/env python3
"""Local OpenAI-compatible bridge to OpenCode's LLM provider.

Runs `opencode serve` as a subprocess (which reuses OpenCode's own stored
credentials, so no API key is needed) and exposes an OpenAI-style
`/v1/chat/completions` + `/v1/models` surface. Hermes (or any OpenAI client,
including Tailrd's OpenAICompatibleAgentBackend) points at this proxy.

    client -> zen_proxy (127.0.0.1:9876, OpenAI API)
            -> opencode serve (127.0.0.1:9875, OpenCode session API)
            -> OpenCode built-in provider (e.g. deepseek-v4-flash-free)

Everything binds to 127.0.0.1 only. `opencode serve` is protected with HTTP
Basic auth via OPENCODE_SERVER_PASSWORD; the OpenAI port has no auth because it
is loopback-only and clients (Hermes) don't send one.

Run standalone:  python -m app.services.zen_proxy
Configuration is via environment variables (see the constants below) so the
proxy can be launched independently of the FastAPI app.
"""

from __future__ import annotations

import atexit
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Configuration (env-driven so this can run without importing the app)
# ---------------------------------------------------------------------------

INTERNAL_PORT = int(os.environ.get("OPENCODE_SERVE_PORT", "9875"))
PROXY_PORT = int(os.environ.get("ZEN_PROXY_PORT", "9876"))
HOST = "127.0.0.1"

# opencode serve enables HTTP Basic auth ONLY when OPENCODE_SERVER_PASSWORD is
# set. We default to no auth because the server binds to 127.0.0.1 (loopback
# only). Set OPENCODE_SERVER_PASSWORD to force auth (e.g. defence in depth on a
# shared host).
SERVER_PASSWORD = os.environ.get("OPENCODE_SERVER_PASSWORD") or None
SERVER_AUTH = (
    base64.b64encode(f"opencode:{SERVER_PASSWORD}".encode()).decode() if SERVER_PASSWORD else None
)


def _auth_headers() -> dict:
    return {"Authorization": f"Basic {SERVER_AUTH}"} if SERVER_AUTH else {}


PROVIDER_ID = os.environ.get("ZEN_PROVIDER_ID", "opencode")
MODEL_ID = os.environ.get("ZEN_MODEL_ID", "deepseek-v4-flash-free")
OPENCODE_COMMAND = os.environ.get("OPENCODE_COMMAND", "opencode")
REQUEST_TIMEOUT = int(os.environ.get("ZEN_PROXY_TIMEOUT_SECONDS", "180"))
SERVE_STARTUP_TIMEOUT = int(os.environ.get("ZEN_PROXY_STARTUP_TIMEOUT_SECONDS", "40"))
# When true (default) the proxy launches `opencode serve` itself (handy locally).
# Set false to bridge to an already-running server (e.g. a separate systemd unit
# supervises `opencode serve`), so each process is restarted independently.
MANAGE_SERVE = os.environ.get("ZEN_PROXY_MANAGE_SERVE", "true").lower() not in ("0", "false", "no")

_opencode_proc: subprocess.Popen | None = None


def _log(msg: str) -> None:
    sys.stderr.write(f"[zen_proxy] {msg}\n")
    sys.stderr.flush()


def _resolve_cli(command: str) -> list[str]:
    """Cross-platform argv prefix to launch a CLI.

    npm installs Windows shims as .cmd/.ps1 which CreateProcess can't execute
    directly, so route them through cmd.exe / PowerShell. On POSIX the resolved
    path (or the bare command) runs directly.
    """
    exe = shutil.which(command) or command
    if sys.platform == "win32":
        low = exe.lower()
        if low.endswith((".cmd", ".bat")):
            return ["cmd.exe", "/c", exe]
        if low.endswith(".ps1"):
            return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", exe]
    return [exe]


# ---------------------------------------------------------------------------
# opencode serve lifecycle
# ---------------------------------------------------------------------------


def start_opencode_serve() -> None:
    global _opencode_proc
    cmd = [
        *_resolve_cli(OPENCODE_COMMAND),
        "serve",
        "--port",
        str(INTERNAL_PORT),
        "--hostname",
        HOST,
    ]
    env = {**os.environ}
    if SERVER_PASSWORD:
        env["OPENCODE_SERVER_PASSWORD"] = SERVER_PASSWORD
    else:
        # Ensure an inherited value doesn't silently switch the server into
        # auth mode when we intend loopback no-auth.
        env.pop("OPENCODE_SERVER_PASSWORD", None)
    _log(f"starting: {' '.join(cmd)} (auth={'on' if SERVER_PASSWORD else 'off'})")
    _opencode_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    atexit.register(stop_opencode_serve)


def stop_opencode_serve() -> None:
    global _opencode_proc
    if _opencode_proc and _opencode_proc.poll() is None:
        _opencode_proc.terminate()
        try:
            _opencode_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _opencode_proc.kill()
    _opencode_proc = None


def wait_for_server(timeout: int = SERVE_STARTUP_TIMEOUT) -> dict | None:
    start = time.time()
    while time.time() - start < timeout:
        # Bail early if the subprocess died on startup.
        if _opencode_proc and _opencode_proc.poll() is not None:
            _log(f"opencode serve exited early (code {_opencode_proc.returncode})")
            return None
        try:
            req = urllib.request.Request(
                f"http://{HOST}:{INTERNAL_PORT}/global/health",
                headers=_auth_headers(),
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                return json.loads(resp.read())
        except Exception:  # noqa: BLE001 - not up yet, keep polling
            time.sleep(0.5)
    return None


def opencode_api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"http://{HOST}:{INTERNAL_PORT}{path}"
    headers = {"Content-Type": "application/json", **_auth_headers()}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "detail": e.read().decode()[:600]}
    except Exception as e:  # noqa: BLE001
        return {"error": True, "status": 502, "detail": str(e)}


# ---------------------------------------------------------------------------
# OpenAI-compatible HTTP surface
# ---------------------------------------------------------------------------


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # noqa: A002 - stdlib signature
        _log(" ".join(str(a) for a in args))

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if urlparse(self.path).path.rstrip("/") == "/v1/models":
            self._send_json(
                {
                    "object": "list",
                    "data": [
                        {
                            "id": MODEL_ID,
                            "object": "model",
                            "created": 1700000000,
                            "owned_by": "opencode-zen",
                        }
                    ],
                }
            )
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):  # noqa: N802
        if urlparse(self.path).path.rstrip("/") != "/v1/chat/completions":
            self._send_json({"error": "not_found"}, 404)
            return

        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_len).decode())
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": f"bad request: {e}"}, 400)
            return

        messages = body.get("messages", [])
        if not messages:
            self._send_json({"error": "no messages"}, 400)
            return

        prompt_text = _messages_to_prompt(messages)
        model_id = _requested_model_id(body)

        session = opencode_api("POST", "/session", {"title": "tailrd-zen"})
        if session.get("error"):
            self._send_json(
                {"error": "LLM unavailable", "detail": str(session.get("detail", ""))}, 502
            )
            return
        sid = session.get("id")
        if not sid:
            self._send_json({"error": "no session id"}, 502)
            return

        try:
            result = opencode_api(
                "POST",
                f"/session/{sid}/message",
                {
                    "parts": [{"type": "text", "text": prompt_text}],
                    "model": {"providerID": PROVIDER_ID, "modelID": model_id},
                },
            )
        finally:
            opencode_api("DELETE", f"/session/{sid}")

        if result.get("error"):
            self._send_json({"error": "LLM failed", "detail": str(result.get("detail", ""))}, 502)
            return

        response_text = "".join(
            part.get("text", "")
            for part in result.get("parts", [])
            if isinstance(part, dict) and part.get("type") == "text"
        )

        self._send_json(
            {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text or "[no response]",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        )


def _messages_to_prompt(messages: list) -> str:
    """Flatten OpenAI chat messages into a single prompt for the session API."""
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            texts = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    texts.append(c.get("text", ""))
                elif not isinstance(c, dict):
                    texts.append(str(c))
            content = " ".join(texts)
        label = {"system": "[System]", "assistant": "[Assistant]"}.get(role, "[User]")
        parts.append(f"{label}\n{content}\n")
    parts.append("[Assistant]\n")
    return "\n".join(parts)


def _requested_model_id(body: dict) -> str:
    """Honour an explicit model in the request, else the configured default.

    Accepts "deepseek-v4-flash-free" or "opencode/deepseek-v4-flash-free".
    """
    requested = body.get("model")
    if isinstance(requested, str) and requested.strip():
        return requested.split("/", 1)[-1]
    return MODEL_ID


def main() -> None:
    if MANAGE_SERVE:
        _log("starting OpenCode server...")
        start_opencode_serve()
    else:
        _log(f"bridging to existing opencode serve on {HOST}:{INTERNAL_PORT}")

    health = wait_for_server()
    if not health:
        _log("ERROR: OpenCode server not reachable")
        if MANAGE_SERVE:
            stop_opencode_serve()
        sys.exit(1)
    _log(f"OpenCode server ready: {health}")

    server = ThreadingHTTPServer((HOST, PROXY_PORT), ProxyHandler)
    _log(
        f"OpenAI bridge on http://{HOST}:{PROXY_PORT}/v1  (model={MODEL_ID}, provider={PROVIDER_ID})"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log("shutting down")
    finally:
        server.server_close()
        stop_opencode_serve()


if __name__ == "__main__":
    main()
