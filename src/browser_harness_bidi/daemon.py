"""WebDriver BiDi WS holder plus IPC relay. One daemon per BIDI_NAME."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any

from . import _ipc as ipc
from .bidi import BiDiClient, BiDiProtocolError


def _load_env_file(path: Path) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace = Path(os.environ.get("BH_AGENT_WORKSPACE", repo_root / "agent-workspace")).expanduser()
    for path in (repo_root / ".env", workspace / ".env"):
        if path.exists():
            _load_env_file(path)


_load_env()

NAME = os.environ.get("BIDI_NAME") or os.environ.get("BU_NAME", "default")
LOG = str(ipc.log_path(NAME))
PID = str(ipc.pid_path(NAME))
BUF = int(os.environ.get("BIDI_EVENT_BUFFER", "500"))
INTERNAL_URL_PREFIXES = ("about:", "chrome:", "chrome-untrusted:", "edge:", "moz-extension:", "chrome-extension:")


def log(message: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def _merge_dict(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def _webdriver_base(url: str) -> str:
    base = url.rstrip("/")
    return base[:-8] if base.endswith("/session") else base


def _webdriver_new_session(url: str) -> dict[str, Any]:
    base = _webdriver_base(url)
    browser_name = os.environ.get("BIDI_BROWSER_NAME", "chrome")
    always: dict[str, Any] = {"browserName": browser_name, "webSocketUrl": True}

    if extra := os.environ.get("BIDI_CAPABILITIES"):
        always = _merge_dict(always, json.loads(extra))

    payload = {"capabilities": {"alwaysMatch": always}}
    request = urllib.request.Request(
        f"{base}/session",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        response = json.loads(urllib.request.urlopen(request, timeout=30).read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"WebDriver session creation failed ({e.code}): {body}") from e

    value = response.get("value", response)
    if isinstance(value, dict) and value.get("error"):
        raise RuntimeError(f"WebDriver session creation failed: {value.get('error')}: {value.get('message')}")

    capabilities = value.get("capabilities", {}) if isinstance(value, dict) else {}
    ws = capabilities.get("webSocketUrl") or value.get("webSocketUrl")
    if not ws:
        raise RuntimeError(
            "WebDriver session did not return capabilities.webSocketUrl. "
            "Make sure the driver/browser supports WebDriver BiDi and accepts webSocketUrl=true."
        )
    return {"ws": ws, "session_ready": True, "webdriver_base": base, "webdriver_session_id": value.get("sessionId")}


def _resolve_endpoint() -> dict[str, Any]:
    if ws := os.environ.get("BIDI_WS") or os.environ.get("WEBDRIVER_BIDI_WS"):
        return {"ws": ws, "session_ready": os.environ.get("BIDI_SESSION_READY") == "1"}

    if webdriver_url := os.environ.get("BIDI_WEBDRIVER_URL") or os.environ.get("WEBDRIVER_URL"):
        return _webdriver_new_session(webdriver_url)

    if port := os.environ.get("BIDI_PORT"):
        host = os.environ.get("BIDI_HOST", "127.0.0.1")
        return {"ws": f"ws://{host}:{port}/session", "session_ready": False}

    raise RuntimeError(
        "No BiDi endpoint configured. Set BIDI_WS for a direct BiDi WebSocket, "
        "or BIDI_WEBDRIVER_URL for ChromeDriver/GeckoDriver with webSocketUrl=true."
    )


def _delete_webdriver_session(base: str, session_id: str) -> None:
    request = urllib.request.Request(f"{base}/session/{session_id}", method="DELETE")
    urllib.request.urlopen(request, timeout=10).read()


def _flatten_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ctx in contexts:
        out.append(ctx)
        out.extend(_flatten_contexts(ctx.get("children") or []))
    return out


def _is_real_context(ctx: dict[str, Any]) -> bool:
    url = ctx.get("url") or ""
    return not url.startswith(INTERNAL_URL_PREFIXES)


class Daemon:
    def __init__(self):
        self.client: BiDiClient | None = None
        self.context: str | None = None
        self.events = deque(maxlen=BUF)
        self.prompt: dict[str, Any] | None = None
        self.stop: asyncio.Event | None = None
        self.webdriver_base: str | None = None
        self.webdriver_session_id: str | None = None

    async def start(self) -> None:
        self.stop = asyncio.Event()
        endpoint = _resolve_endpoint()
        self.webdriver_base = endpoint.get("webdriver_base")
        self.webdriver_session_id = endpoint.get("webdriver_session_id")
        log(f"connecting to {endpoint['ws']}")
        self.client = BiDiClient(endpoint["ws"], on_event=self._on_event)
        await self.client.start()

        if not endpoint.get("session_ready"):
            try:
                result = await self.client.send("session.new", {"capabilities": {}})
                log(f"session.new -> {result.get('sessionId', '(no session id)')}")
            except BiDiProtocolError as e:
                raise RuntimeError(f"session.new failed: {e}") from e

        await self._subscribe_default_events()
        await self.attach_first_context()

    async def shutdown(self) -> None:
        if self.client is not None:
            try:
                await self.client.close()
            except Exception as e:
                log(f"client close failed: {e}")
        if (
            self.webdriver_base
            and self.webdriver_session_id
            and os.environ.get("BIDI_DELETE_WEBDRIVER_SESSION") == "1"
        ):
            try:
                _delete_webdriver_session(self.webdriver_base, self.webdriver_session_id)
                log(f"deleted webdriver session {self.webdriver_session_id}")
            except Exception as e:
                log(f"delete webdriver session failed: {e}")

    async def _subscribe_default_events(self) -> None:
        assert self.client is not None
        core_events = [
            "browsingContext.contextCreated",
            "browsingContext.contextDestroyed",
            "browsingContext.domContentLoaded",
            "browsingContext.load",
            "browsingContext.navigationStarted",
            "browsingContext.fragmentNavigated",
            "browsingContext.userPromptOpened",
            "browsingContext.userPromptClosed",
            "log.entryAdded",
        ]
        network_events = [
            "network.beforeRequestSent",
            "network.responseStarted",
            "network.responseCompleted",
            "network.fetchError",
        ]
        for events in (core_events + network_events, core_events):
            try:
                await self.client.send("session.subscribe", {"events": events})
                return
            except Exception as e:
                log(f"session.subscribe failed for {len(events)} events: {e}")
        log("continuing without event subscription")

    def _on_event(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        self.events.append({"method": method, "params": params})
        if method == "browsingContext.userPromptOpened":
            self.prompt = params
        elif method == "browsingContext.userPromptClosed":
            self.prompt = None

    async def contexts(self) -> list[dict[str, Any]]:
        assert self.client is not None
        result = await self.client.send("browsingContext.getTree", {})
        return _flatten_contexts(result.get("contexts", []))

    async def attach_first_context(self) -> dict[str, Any]:
        assert self.client is not None
        contexts = await self.contexts()
        real = [ctx for ctx in contexts if _is_real_context(ctx)]
        if not real:
            created = await self.client.send("browsingContext.create", {"type": "tab"})
            self.context = created["context"]
            log(f"created context {self.context}")
            return {"context": self.context, "url": "about:blank"}
        self.context = real[0]["context"]
        log(f"attached context {self.context} ({real[0].get('url', '')[:100]})")
        return real[0]

    async def handle(self, req: dict[str, Any]) -> dict[str, Any]:
        expected = ipc.expected_token()
        if expected is not None and req.get("token") != expected:
            return {"error": "unauthorized"}

        meta = req.get("meta")
        if meta == "ping":
            return {"pong": True, "pid": os.getpid()}
        if meta == "drain_events":
            out = list(self.events)
            self.events.clear()
            return {"events": out}
        if meta == "current_context":
            return {"context": self.context}
        if meta == "set_context":
            self.context = req.get("context") or self.context
            return {"context": self.context}
        if meta == "pending_prompt":
            return {"prompt": self.prompt}
        if meta == "connection_status":
            try:
                contexts = await self.contexts()
                current = next((ctx for ctx in contexts if ctx.get("context") == self.context), None)
                return {"context": self.context, "current": current, "contexts": contexts}
            except Exception as e:
                return {"error": f"bidi_disconnected: {e}"}
        if meta == "shutdown":
            assert self.stop is not None
            self.stop.set()
            return {"ok": True}

        assert self.client is not None
        method = req["method"]
        params = req.get("params") or {}
        try:
            return {"result": await self.client.send(method, params)}
        except Exception as e:
            return {"error": str(e)}


async def serve(daemon: Daemon) -> None:
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await reader.readline()
            if not line:
                return
            response = await daemon.handle(json.loads(line))
            writer.write((json.dumps(response, default=str) + "\n").encode())
            await writer.drain()
        except Exception as e:
            log(f"conn: {e}")
            try:
                writer.write((json.dumps({"error": str(e)}) + "\n").encode())
                await writer.drain()
            except Exception:
                pass
        finally:
            writer.close()

    assert daemon.stop is not None
    serve_task = asyncio.create_task(ipc.serve(NAME, handler))
    stop_task = asyncio.create_task(daemon.stop.wait())
    await asyncio.sleep(0.05)
    log(f"listening on {ipc.sock_addr(NAME)} (name={NAME})")
    try:
        done, _ = await asyncio.wait({serve_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
        if serve_task in done:
            await serve_task
    finally:
        for task in (serve_task, stop_task):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        ipc.cleanup_endpoint(NAME)


async def main_async() -> None:
    daemon = Daemon()
    try:
        await daemon.start()
        await serve(daemon)
    finally:
        await daemon.shutdown()


def already_running() -> bool:
    return ipc.ping(NAME, timeout=1.0)


if __name__ == "__main__":
    if already_running():
        print(f"daemon already running on {ipc.sock_addr(NAME)}", file=sys.stderr)
        sys.exit(0)
    open(LOG, "w", encoding="utf-8").close()
    Path(PID).write_text(str(os.getpid()))
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"fatal: {e}")
        sys.exit(1)
    finally:
        try:
            os.unlink(PID)
        except FileNotFoundError:
            pass
