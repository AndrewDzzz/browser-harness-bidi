"""Daemon IPC plumbing for bidi-harness.

POSIX uses an AF_UNIX socket. Windows uses TCP loopback plus a per-daemon token,
because AF_UNIX is not reliably available in every Python distribution there.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

BIDI_TMP_DIR = os.environ.get("BIDI_TMP_DIR") or os.environ.get("BH_TMP_DIR")
BIDI_RUNTIME_DIR = os.environ.get("BIDI_RUNTIME_DIR") or os.environ.get("BH_RUNTIME_DIR") or BIDI_TMP_DIR

_TMP = Path(BIDI_TMP_DIR or (tempfile.gettempdir() if IS_WINDOWS else "/tmp"))
_RUNTIME = Path(BIDI_RUNTIME_DIR or (tempfile.gettempdir() if IS_WINDOWS else "/tmp"))
_TMP.mkdir(parents=True, exist_ok=True)
_RUNTIME.mkdir(parents=True, exist_ok=True)

_NAME_RE = re.compile(r"\A[A-Za-z0-9_-]{1,64}\Z")
_server_token: str | None = None


def _check(name: str) -> str:
    if not _NAME_RE.match(name or ""):
        raise ValueError(f"invalid BIDI_NAME {name!r}: must match [A-Za-z0-9_-]{{1,64}}")
    return name


def _runtime_stem(name: str) -> str:
    _check(name)
    return "bidi" if BIDI_RUNTIME_DIR else f"bidi-{name}"


def _tmp_stem(name: str) -> str:
    _check(name)
    return "bidi" if BIDI_TMP_DIR else f"bidi-{name}"


def log_path(name: str) -> Path:
    return _TMP / f"{_tmp_stem(name)}.log"


def pid_path(name: str) -> Path:
    return _RUNTIME / f"{_runtime_stem(name)}.pid"


def port_path(name: str) -> Path:
    return _RUNTIME / f"{_runtime_stem(name)}.port"


def _sock_path(name: str) -> Path:
    return _RUNTIME / f"{_runtime_stem(name)}.sock"


def sock_addr(name: str) -> str:
    if not IS_WINDOWS:
        return str(_sock_path(name))
    port, _ = _read_port_file(name)
    return f"127.0.0.1:{port}" if port else f"tcp:{_runtime_stem(name)}"


def _read_port_file(name: str) -> tuple[int | None, str | None]:
    try:
        data = json.loads(port_path(name).read_text())
        return int(data["port"]), data["token"]
    except (FileNotFoundError, ValueError, KeyError, TypeError, OSError, json.JSONDecodeError):
        return None, None


def spawn_kwargs() -> dict:
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def connect(name: str, timeout: float = 1.0) -> tuple[socket.socket, str | None]:
    if not IS_WINDOWS:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(str(_sock_path(name)))
        return s, None
    port, token = _read_port_file(name)
    if port is None:
        raise FileNotFoundError(str(port_path(name)))
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    s.settimeout(timeout)
    return s, token


def request(c: socket.socket, token: str | None, req: dict) -> dict:
    if token:
        req = {**req, "token": token}
    c.sendall((json.dumps(req) + "\n").encode())
    data = b""
    while not data.endswith(b"\n"):
        chunk = c.recv(1 << 16)
        if not chunk:
            break
        data += chunk
    return json.loads(data or b"{}")


def ping(name: str, timeout: float = 1.0) -> bool:
    try:
        c, token = connect(name, timeout=timeout)
    except (FileNotFoundError, ConnectionRefusedError, TimeoutError, socket.timeout, OSError):
        return False
    try:
        resp = request(c, token, {"meta": "ping"})
        return isinstance(resp, dict) and resp.get("pong") is True
    except (OSError, ValueError, AttributeError, json.JSONDecodeError):
        return False
    finally:
        try:
            c.close()
        except OSError:
            pass


def identify(name: str, timeout: float = 1.0) -> int | None:
    try:
        c, token = connect(name, timeout=timeout)
    except (FileNotFoundError, ConnectionRefusedError, TimeoutError, socket.timeout, OSError):
        return None
    try:
        resp = request(c, token, {"meta": "ping"})
        if not isinstance(resp, dict) or resp.get("pong") is not True:
            return None
        pid = resp.get("pid")
        return pid if type(pid) is int and 0 < pid < (1 << 31) else None
    except (OSError, ValueError, AttributeError, json.JSONDecodeError):
        return None
    finally:
        try:
            c.close()
        except OSError:
            pass


async def serve(name: str, handler):
    global _server_token
    if not IS_WINDOWS:
        path = str(_sock_path(name))
        if os.path.exists(path):
            os.unlink(path)
        old_umask = os.umask(0o077)
        try:
            server = await asyncio.start_unix_server(handler, path=path)
        finally:
            os.umask(old_umask)
        _server_token = None
        async with server:
            await asyncio.Event().wait()
        return

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    _server_token = secrets.token_hex(32)
    pf = port_path(name)
    tmp = pf.with_name(pf.name + ".tmp")
    tmp.write_text(json.dumps({"port": port, "token": _server_token}))
    os.replace(tmp, pf)
    try:
        async with server:
            await asyncio.Event().wait()
    finally:
        try:
            pf.unlink()
        except FileNotFoundError:
            pass


def expected_token() -> str | None:
    return _server_token


def cleanup_endpoint(name: str) -> None:
    p = port_path(name) if IS_WINDOWS else _sock_path(name)
    try:
        p.unlink()
    except FileNotFoundError:
        pass
