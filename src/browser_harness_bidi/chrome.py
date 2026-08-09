"""Managed Chrome launcher for bidi-harness.

This is a convenience wrapper around chromedriver + Chrome WebDriver BiDi. It
keeps Chrome on the standard WebDriver path: chromedriver creates a session with
webSocketUrl=true, then the harness connects to the returned BiDi WebSocket.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_driver(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/status"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5).read()
            return
        except Exception as e:
            last_error = e
            time.sleep(0.15)
    raise RuntimeError(f"chromedriver did not become ready on {url}: {last_error}")


def _merge_dict(base: dict, extra: dict) -> dict:
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def _normalize_chrome_arg(arg: str) -> str:
    value = str(arg).strip()
    if not value:
        raise ValueError("--argument cannot be empty")
    return value if value.startswith("-") else f"--{value}"


def _normalize_window_size(value: str) -> str:
    text = str(value).strip().lower().replace(",", "x")
    parts = text.split("x", 1)
    if len(parts) != 2:
        raise ValueError("--window-size must look like WIDTHxHEIGHT")
    width = int(parts[0])
    height = int(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError("--window-size values must be positive")
    return f"{width},{height}"


def _chrome_args(args: argparse.Namespace) -> list[str]:
    chrome_args = ["--no-first-run", "--no-default-browser-check"]

    if args.headless:
        chrome_args.append("--headless=new")
    if args.user_data_dir:
        chrome_args.append(f"--user-data-dir={Path(args.user_data_dir).expanduser()}")
    if args.profile_directory:
        chrome_args.append(f"--profile-directory={args.profile_directory}")
    if args.incognito:
        chrome_args.append("--incognito")
    if args.proxy_server:
        chrome_args.append(f"--proxy-server={args.proxy_server}")
    if args.window_size:
        chrome_args.append(f"--window-size={_normalize_window_size(args.window_size)}")

    for arg in args.argument or []:
        chrome_args.append(_normalize_chrome_arg(arg))

    return chrome_args


def _build_capabilities(args: argparse.Namespace) -> dict:
    chrome_options: dict[str, object] = {}

    if args.debugger_address:
        chrome_options["debuggerAddress"] = args.debugger_address
    else:
        chrome_options["args"] = _chrome_args(args)
        if args.chrome_binary:
            chrome_options["binary"] = str(Path(args.chrome_binary).expanduser())

    capabilities: dict[str, object] = {"goog:chromeOptions": chrome_options}
    if args.capabilities:
        extra = json.loads(args.capabilities)
        capabilities = _merge_dict(capabilities, extra)
    return capabilities


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bidi-chrome",
        description="Run bidi-harness through a managed local chromedriver + Chrome WebDriver BiDi session.",
    )
    parser.add_argument("--port", type=int, default=0, help="chromedriver port; default chooses a free port")
    parser.add_argument("--name", default=None, help="BIDI_NAME namespace for this managed session")
    parser.add_argument("--headed", action="store_true", help="show Chrome instead of running headless")
    parser.add_argument("--user-data-dir", default=None, help="Chrome user data directory to use")
    parser.add_argument("--profile-directory", default=None, help="Chrome profile directory name inside user-data-dir")
    parser.add_argument("--incognito", action="store_true", help="launch Chrome incognito mode")
    parser.add_argument("--proxy-server", default=None, help="Chrome proxy server, for example http://127.0.0.1:8080")
    parser.add_argument("--window-size", default=None, help="Chrome window size as WIDTHxHEIGHT")
    parser.add_argument("--argument", action="append", default=[], help="extra Chrome argument; repeat as needed")
    parser.add_argument(
        "--chrome-binary",
        "--browser-path",
        dest="chrome_binary",
        default=None,
        help="path to Chrome/Chromium executable",
    )
    parser.add_argument(
        "--debugger-address",
        default=None,
        help="attach ChromeDriver to an already-running Chrome debug address, such as 127.0.0.1:9222",
    )
    parser.add_argument("--capabilities", default=None, help="JSON object merged into WebDriver alwaysMatch capabilities")
    parser.add_argument("--chromedriver", default="chromedriver", help="path to chromedriver")
    parser.add_argument("--keep-daemon", action="store_true", help="leave the daemon alive after the script exits")
    parser.add_argument("--keep-browser", action="store_true", help="do not delete the WebDriver session on shutdown")
    parser.add_argument("--doctor", action="store_true", help="print the underlying bidi-harness doctor output")
    return parser


def main() -> None:
    parser = _parser()
    args, rest = parser.parse_known_args()
    if rest:
        parser.error(f"unexpected arguments: {' '.join(rest)}")

    args.headless = not args.headed
    port = args.port or _free_port()
    name = args.name or os.environ.get("BIDI_NAME") or "chrome"
    log_path = Path(tempfile.gettempdir()) / f"bidi-chrome-{name}.chromedriver.log"

    env = os.environ.copy()
    env["BIDI_NAME"] = name
    env["BIDI_WEBDRIVER_URL"] = f"http://127.0.0.1:{port}"
    env["BIDI_BROWSER_NAME"] = "chrome"
    env["BIDI_CAPABILITIES"] = json.dumps(_build_capabilities(args))
    env.setdefault("BIDI_DELETE_WEBDRIVER_SESSION", "0" if args.keep_browser else "1")

    driver_path = Path(args.chromedriver).expanduser()
    if not shutil.which(args.chromedriver) and not driver_path.exists():
        raise SystemExit(f"chromedriver not found: {args.chromedriver}")

    cmd = [str(driver_path) if driver_path.exists() else args.chromedriver, f"--port={port}"]
    with open(log_path, "a", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env)
    old_env = os.environ.copy()
    os.environ.update(env)
    try:
        _wait_for_driver(port)
        if args.doctor:
            from .admin import ensure_daemon, run_doctor

            ensure_daemon()
            code = run_doctor()
            if code:
                raise SystemExit(code)
        else:
            from .run import main as harness_main

            sys.argv = ["bidi-harness"]
            harness_main()
    finally:
        if not args.keep_daemon:
            try:
                from .admin import restart_daemon

                restart_daemon()
            except Exception:
                pass
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        os.environ.clear()
        os.environ.update(old_env)


if __name__ == "__main__":
    main()
