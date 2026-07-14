"""Small admin helpers for the bidi-harness CLI."""

from __future__ import annotations

import importlib.metadata
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from . import _ipc as ipc


def _name() -> str:
    return os.environ.get("BIDI_NAME") or os.environ.get("BU_NAME", "default")


def _version() -> str | None:
    try:
        return importlib.metadata.version("browser-harness-bidi")
    except importlib.metadata.PackageNotFoundError:
        try:
            from . import __version__

            return __version__
        except Exception:
            return None


def _log_tail(name: str | None = None) -> str | None:
    try:
        lines = ipc.log_path(name or _name()).read_text(encoding="utf-8", errors="replace").strip().splitlines()
        return lines[-1] if lines else None
    except FileNotFoundError:
        return None


def daemon_alive(name: str | None = None) -> bool:
    return ipc.ping(name or _name(), timeout=1.0)


def _daemon_request(req: dict, timeout: float = 5.0, name: str | None = None) -> dict:
    c, token = ipc.connect(name or _name(), timeout=timeout)
    try:
        return ipc.request(c, token, req)
    finally:
        c.close()


def ensure_daemon(timeout: float = 15.0) -> None:
    name = _name()
    if daemon_alive(name):
        return
    log_file = open(ipc.log_path(name), "a", encoding="utf-8")
    subprocess.Popen(
        [sys.executable, "-m", "browser_harness_bidi.daemon"],
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=log_file,
        env=os.environ.copy(),
        **ipc.spawn_kwargs(),
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        if daemon_alive(name):
            return
        time.sleep(0.2)
    tail = _log_tail(name)
    suffix = f" Last log line: {tail}" if tail else ""
    raise RuntimeError(f"bidi-harness daemon did not start within {timeout:.0f}s.{suffix}")


def restart_daemon() -> None:
    name = _name()
    if daemon_alive(name):
        try:
            _daemon_request({"meta": "shutdown"}, timeout=2.0, name=name)
        except Exception:
            pass
        for _ in range(30):
            if not daemon_alive(name):
                return
            time.sleep(0.1)
    pid = ipc.identify(name, timeout=0.5)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def connection_status() -> dict:
    return _daemon_request({"meta": "connection_status"}, timeout=10.0)


def run_doctor() -> int:
    name = _name()
    print(f"browser-harness-bidi version: {_version() or 'unknown'}")
    print(f"name: {name}")
    print(f"runtime endpoint: {ipc.sock_addr(name)}")
    print(f"daemon alive: {'yes' if daemon_alive(name) else 'no'}")
    print(f"BIDI_WS: {'set' if os.environ.get('BIDI_WS') else 'not set'}")
    print(f"BIDI_WEBDRIVER_URL: {os.environ.get('BIDI_WEBDRIVER_URL') or 'not set'}")
    print(f"BIDI_BROWSER_NAME: {os.environ.get('BIDI_BROWSER_NAME') or 'chrome'}")
    if not (os.environ.get("BIDI_WS") or os.environ.get("BIDI_WEBDRIVER_URL") or os.environ.get("BIDI_PORT")):
        print("connection hint: set BIDI_WS, BIDI_PORT, or BIDI_WEBDRIVER_URL")
    if daemon_alive(name):
        status = connection_status()
        print("connection status:")
        print(json.dumps(status, indent=2, default=str))
    elif tail := _log_tail(name):
        print(f"last log line: {tail}")
    return 0
