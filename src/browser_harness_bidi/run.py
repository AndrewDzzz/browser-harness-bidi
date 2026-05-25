from __future__ import annotations

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .admin import _version, ensure_daemon, restart_daemon, run_doctor
from .helpers import *  # noqa: F403,F401

HELP = """bidi-harness

WebDriver bidi browser harness. Helpers are pre-imported and the daemon auto-starts.

Typical usage:
  bidi-harness <<'PY'
  new_tab("https://example.com")
  wait_for_load()
  print(page_info())
  PY

Connection:
  Set BIDI_WS for a direct bidi websocket, or BIDI_WEBDRIVER_URL for a WebDriver broker.

Commands:
  bidi-harness --version   print installed version
  bidi-harness --doctor    diagnose daemon and endpoint configuration
  bidi-harness doctor      same as --doctor
  bidi-harness --reload    stop daemon so next call starts fresh
"""

USAGE = """Usage: bidi-harness <<'PY'
print(page_info())
PY
"""


def main():
    args = sys.argv[1:]
    if args and args[0] in {"-h", "--help"}:
        print(HELP)
        return
    if args and args[0] == "--version":
        print(_version() or "unknown")
        return
    if args and args[0] in {"--doctor", "doctor"}:
        sys.exit(run_doctor())
    if args and args[0] == "--reload":
        restart_daemon()
        print("daemon stopped; it will restart on the next call")
        return
    if args or sys.stdin.isatty():
        sys.exit(USAGE)

    code = sys.stdin.read()
    if not code.strip():
        sys.exit(USAGE)
    ensure_daemon()
    exec(compile(code, "<bidi-harness>", "exec"), globals())


if __name__ == "__main__":
    main()
