"""ruyiPage-compatible Firefox launcher for bidi-harness.

ruyiPage's Firefox route exposes WebDriver BiDi directly from Firefox Remote
Agent, usually at ws://host:port/session. This wrapper follows that shape:
launch a Firefox-compatible runtime with --remote-debugging-port, then point the
harness daemon at the direct BiDi WebSocket.
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
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _split_address(address: str) -> tuple[str, int]:
    host, port = str(address).rsplit(":", 1)
    return host, int(port)


def _path_for_executable(path: str | os.PathLike[str]) -> str:
    expanded = Path(path).expanduser()
    if expanded.is_dir():
        exe_name = "firefox.exe" if sys.platform == "win32" else "firefox"
        expanded = expanded / exe_name
    return str(expanded)


def _system_firefox_path() -> str | None:
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ]
        found = shutil.which("firefox.exe") or shutil.which("firefox")
    elif sys.platform == "darwin":
        candidates = ["/Applications/Firefox.app/Contents/MacOS/firefox"]
        found = shutil.which("firefox")
    else:
        candidates = ["/usr/bin/firefox", "/usr/local/bin/firefox", "/snap/bin/firefox"]
        found = shutil.which("firefox")

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return found


def _ruyipage_firefox_path() -> str | None:
    try:
        from ruyipage import resolve_firefox_path
    except Exception:
        return None

    for kwargs in ({"allow_system": False}, {}):
        try:
            path = resolve_firefox_path(**kwargs)
        except TypeError:
            continue
        except Exception:
            return None
        if path:
            return str(path)
    return None


def _default_browser_path(explicit_path: str | None = None) -> str | None:
    if explicit_path:
        return _path_for_executable(explicit_path)
    return _ruyipage_firefox_path() or _system_firefox_path()


def _is_executable_available(path: str) -> bool:
    if os.path.sep not in path and (os.path.altsep is None or os.path.altsep not in path):
        return shutil.which(path) is not None
    return Path(path).exists()


def _is_bidi_ws_url(ws_url: str) -> bool:
    if not ws_url:
        return False
    try:
        path = urlsplit(ws_url).path.lower()
    except Exception:
        return False
    return "/devtools/" not in path


def _read_json_ws_url(host: str, port: int, timeout: float) -> str:
    url = f"http://{host}:{port}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return ""

    if isinstance(data, dict):
        ws = data.get("webSocketDebuggerUrl", "")
        return ws if _is_bidi_ws_url(ws) else ""

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            ws = item.get("webSocketDebuggerUrl", "")
            if _is_bidi_ws_url(ws):
                return ws
    return ""


def _resolve_bidi_ws(host: str, port: int, timeout: float = 5.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ws = _read_json_ws_url(host, port, timeout=0.5)
        if ws:
            return ws
        time.sleep(0.1)
    return f"ws://{host}:{port}/session"


def _wait_for_bidi_endpoint(host: str, port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, int(port)), timeout=0.5):
                return
        except Exception as e:
            last_error = e
            time.sleep(0.15)
    raise RuntimeError(f"Firefox Remote Agent did not become ready on {host}:{port}: {last_error}")


def _parse_pref_value(value: str) -> object:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _parse_pref(raw: str) -> tuple[str, object]:
    if "=" not in raw:
        raise ValueError("--pref must look like key=value")
    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError("--pref key cannot be empty")
    return key, _parse_pref_value(value.strip())


def _prefs_from_args(args: argparse.Namespace) -> dict[str, object]:
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
    for raw in args.pref or []:
        key, value = _parse_pref(raw)
        prefs[key] = value
    return prefs


def _write_user_prefs(profile_path: str, prefs: dict[str, object]) -> None:
    if not prefs:
        return
    profile = Path(profile_path).expanduser()
    profile.mkdir(parents=True, exist_ok=True)
    user_js = profile / "user.js"
    lines = ["", "// browser-harness-bidi ruyi-firefox prefs"]
    for key, value in prefs.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        else:
            rendered = json.dumps(str(value))
        lines.append(f'user_pref("{key}", {rendered});')
    with open(user_js, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _firefox_arguments(args: argparse.Namespace, port: int, profile_path: str | None) -> list[str]:
    firefox_args = [f"--remote-debugging-port={port}", "--no-remote"]

    if args.marionette:
        firefox_args.append("--marionette")
    if profile_path:
        firefox_args.extend(["--profile", str(Path(profile_path).expanduser())])
    if args.headless:
        firefox_args.append("--headless")
    if args.private:
        firefox_args.append("-private")
    if args.fpfile:
        firefox_args.append(f"--fpfile={Path(args.fpfile).expanduser()}")

    for raw in args.argument or []:
        value = str(raw).strip()
        if not value:
            raise ValueError("--argument cannot be empty")
        firefox_args.append(value)

    if not args.no_startup_url and args.startup_url:
        firefox_args.append(args.startup_url)

    return firefox_args


def _build_command(args: argparse.Namespace, port: int, profile_path: str | None, browser_path: str) -> list[str]:
    return [browser_path, *_firefox_arguments(args, port, profile_path)]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bidi-ruyi-firefox",
        description="Run bidi-harness through a ruyiPage-compatible direct Firefox WebDriver BiDi session.",
    )
    parser.add_argument("--port", type=int, default=0, help="Firefox remote debugging port; default chooses a free port")
    parser.add_argument("--name", default=None, help="BIDI_NAME namespace for this managed session")
    parser.add_argument("--headed", action="store_true", help="show Firefox instead of running headless")
    parser.add_argument("--private", action="store_true", help="launch Firefox private browsing mode")
    parser.add_argument("--profile", "--user-dir", dest="profile", default=None, help="Firefox profile/user directory")
    parser.add_argument("--fpfile", default=None, help="ruyiPage/firefox-fingerprintBrowser fpfile path")
    parser.add_argument("--browser-path", default=None, help="path to Firefox or ruyiPage Firefox executable")
    parser.add_argument("--existing-address", default=None, help="attach to an existing host:port instead of launching Firefox")
    parser.add_argument("--bidi-ws", default=None, help="direct BiDi WebSocket URL; implies existing connection mode")
    parser.add_argument("--session-ready", action="store_true", help="set BIDI_SESSION_READY=1 for an existing session WebSocket")
    parser.add_argument("--startup-url", default="about:blank", help="startup URL for managed launches")
    parser.add_argument("--no-startup-url", action="store_true", help="do not append a startup URL")
    parser.add_argument("--no-marionette", dest="marionette", action="store_false", help="do not pass --marionette")
    parser.set_defaults(marionette=True)
    parser.add_argument(
        "--privacy-profile",
        action="store_true",
        help="write official Firefox privacy-hardening prefs; this does not hide WebDriver automation",
    )
    parser.add_argument("--pref", action="append", default=[], help="append a Firefox user.js preference as key=value")
    parser.add_argument("--argument", action="append", default=[], help="extra Firefox argument; repeat as needed")
    parser.add_argument("--keep-daemon", action="store_true", help="leave the daemon alive after the script exits")
    parser.add_argument("--keep-browser", action="store_true", help="leave a managed Firefox process alive after the script exits")
    parser.add_argument("--keep-profile", action="store_true", help="do not delete the temporary profile after shutdown")
    parser.add_argument("--doctor", action="store_true", help="print the underlying bidi-harness doctor output")
    return parser


def _run_harness(args: argparse.Namespace, env: dict[str, str]) -> None:
    old_env = os.environ.copy()
    os.environ.update(env)
    try:
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
        os.environ.clear()
        os.environ.update(old_env)


def main() -> None:
    parser = _parser()
    args, rest = parser.parse_known_args()
    if rest:
        parser.error(f"unexpected arguments: {' '.join(rest)}")

    args.headless = not args.headed
    name = args.name or os.environ.get("BIDI_NAME") or "ruyi-firefox"
    proc: subprocess.Popen | None = None
    auto_profile: str | None = None

    if args.bidi_ws:
        ws_url = args.bidi_ws
    elif args.existing_address:
        host, port = _split_address(args.existing_address)
        _wait_for_bidi_endpoint(host, port)
        ws_url = _resolve_bidi_ws(host, port)
    else:
        host = "127.0.0.1"
        port = args.port or _free_port()
        browser_path = _default_browser_path(args.browser_path)
        if not browser_path:
            raise SystemExit("Firefox runtime not found. Pass --browser-path or install ruyiPage's Firefox runtime.")
        if not _is_executable_available(browser_path):
            raise SystemExit(f"Firefox runtime not found: {browser_path}")

        profile_path = args.profile
        if not profile_path:
            auto_profile = tempfile.mkdtemp(prefix="bidi-ruyi-firefox-")
            profile_path = auto_profile
        Path(profile_path).expanduser().mkdir(parents=True, exist_ok=True)
        _write_user_prefs(profile_path, _prefs_from_args(args))

        cmd = _build_command(args, port, profile_path, browser_path)
        log_path = Path(tempfile.gettempdir()) / f"bidi-ruyi-firefox-{name}.firefox.log"
        with open(log_path, "a", encoding="utf-8") as log:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                env=os.environ.copy(),
                start_new_session=(sys.platform != "win32"),
            )
        _wait_for_bidi_endpoint(host, port)
        ws_url = _resolve_bidi_ws(host, port)

    env = os.environ.copy()
    env["BIDI_NAME"] = name
    env["BIDI_WS"] = ws_url
    env["BIDI_BROWSER_NAME"] = "firefox"
    env.pop("BIDI_WEBDRIVER_URL", None)
    env.pop("WEBDRIVER_URL", None)
    env.pop("BIDI_CAPABILITIES", None)
    if args.session_ready:
        env["BIDI_SESSION_READY"] = "1"
    else:
        env.pop("BIDI_SESSION_READY", None)

    try:
        _run_harness(args, env)
    finally:
        if proc is not None and not args.keep_browser:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if auto_profile and not args.keep_profile and not args.keep_browser:
            shutil.rmtree(auto_profile, ignore_errors=True)


if __name__ == "__main__":
    main()
