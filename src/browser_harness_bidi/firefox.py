"""Managed Firefox launcher for bidi-harness.

This is a convenience wrapper around geckodriver + Firefox WebDriver bidi. It
keeps the harness bidi-first while removing the setup tax for local use.
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

from .admin import restart_daemon
from .run import main as harness_main


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
    raise RuntimeError(f"geckodriver did not become ready on {url}: {last_error}")


def _build_capabilities(args: argparse.Namespace) -> dict:
    firefox_args = []
    if args.headless:
        firefox_args.append("-headless")
    if args.private:
        firefox_args.append("-private")
    if args.profile:
        firefox_args.extend(["-profile", str(Path(args.profile).expanduser())])

    prefs: dict[str, object] = {}
    if args.privacy_profile:
        prefs.update(
            {
                "privacy.resistFingerprinting": True,
                "privacy.trackingprotection.enabled": True,
                "privacy.trackingprotection.socialtracking.enabled": True,
                "privacy.partition.network_state": True,
                "network.cookie.cookieBehavior": 5,
                "media.peerconnection.enabled": False,
                "webgl.disabled": True,
            }
        )

    options: dict[str, object] = {}
    if firefox_args:
        options["args"] = firefox_args
    if prefs:
        options["prefs"] = prefs

    capabilities: dict[str, object] = {"moz:firefoxOptions": options} if options else {}
    if args.capabilities:
        extra = json.loads(args.capabilities)
        capabilities = _merge_dict(capabilities, extra)
    return capabilities


def _merge_dict(base: dict, extra: dict) -> dict:
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_dict(out[key], value)
        else:
            out[key] = value
    return out


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bidi-firefox",
        description="Run bidi-harness through a managed local geckodriver + Firefox WebDriver bidi session.",
    )
    parser.add_argument("--port", type=int, default=0, help="geckodriver port; default chooses a free port")
    parser.add_argument("--name", default=None, help="BIDI_NAME namespace for this managed session")
    parser.add_argument("--headed", action="store_true", help="show Firefox instead of running headless")
    parser.add_argument("--private", action="store_true", help="launch Firefox private browsing mode")
    parser.add_argument("--profile", default=None, help="Firefox profile directory to use")
    parser.add_argument(
        "--privacy-profile",
        action="store_true",
        help="enable official Firefox privacy-hardening prefs; this does not hide WebDriver automation",
    )
    parser.add_argument("--capabilities", default=None, help="JSON object merged into WebDriver alwaysMatch capabilities")
    parser.add_argument("--geckodriver", default="geckodriver", help="path to geckodriver")
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
    name = args.name or os.environ.get("BIDI_NAME") or "firefox"
    log_path = Path(tempfile.gettempdir()) / f"bidi-firefox-{name}.geckodriver.log"

    env = os.environ.copy()
    env["BIDI_NAME"] = name
    env["BIDI_WEBDRIVER_URL"] = f"http://127.0.0.1:{port}"
    env["BIDI_BROWSER_NAME"] = "firefox"
    env["BIDI_CAPABILITIES"] = json.dumps(_build_capabilities(args))
    env.setdefault("BIDI_DELETE_WEBDRIVER_SESSION", "0" if args.keep_browser else "1")

    if not shutil.which(args.geckodriver) and not Path(args.geckodriver).exists():
        raise SystemExit(f"geckodriver not found: {args.geckodriver}")

    cmd = [args.geckodriver, "--host", "127.0.0.1", "--port", str(port)]
    with open(log_path, "a", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env)
    old_env = os.environ.copy()
    os.environ.update(env)
    try:
        _wait_for_driver(port)
        if args.doctor:
            sys.argv = ["bidi-harness", "--doctor"]
        else:
            sys.argv = ["bidi-harness"]
        harness_main()
    finally:
        if not args.keep_daemon:
            try:
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
