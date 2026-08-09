import os
import sys

import browser_harness_bidi.admin as admin
import browser_harness_bidi.ruyi_firefox as ruyi


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


def _parse(args):
    parsed = ruyi._parser().parse_args(args)
    parsed.headless = not parsed.headed
    return parsed


def test_ruyi_firefox_command_includes_direct_bidi_and_fpfile():
    args = _parse(
        [
            "--browser-path",
            "/opt/ruyi/firefox",
            "--profile",
            "~/ruyi-profile",
            "--fpfile",
            "~/fp.txt",
            "--argument=--some-custom-flag",
        ]
    )

    cmd = ruyi._build_command(args, 12000, args.profile, "/opt/ruyi/firefox")

    assert cmd[:4] == ["/opt/ruyi/firefox", "--remote-debugging-port=12000", "--no-remote", "--marionette"]
    assert "--profile" in cmd
    assert any(part.endswith("ruyi-profile") for part in cmd)
    assert any(part.startswith("--fpfile=") and part.endswith("fp.txt") for part in cmd)
    assert "--headless" in cmd
    assert "--some-custom-flag" in cmd
    assert cmd[-1] == "about:blank"


def test_ruyi_firefox_existing_doctor_uses_direct_bidi_ws(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["bidi-ruyi-firefox", "--name", "ruyi-test", "--existing-address", "127.0.0.1:12000", "--doctor"])
    monkeypatch.setattr(ruyi, "_wait_for_bidi_endpoint", lambda host, port: calls.append(("wait", host, port)))
    monkeypatch.setattr(ruyi, "_resolve_bidi_ws", lambda host, port: "ws://127.0.0.1:12000/session")
    monkeypatch.setattr(
        ruyi.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append(("popen", args[0])) or FakeProcess(),
    )
    monkeypatch.setattr(admin, "ensure_daemon", lambda: calls.append(("ensure_daemon", os.environ.get("BIDI_WS"))))
    monkeypatch.setattr(admin, "run_doctor", lambda: calls.append(("run_doctor", os.environ.get("BIDI_NAME"))) or 0)
    monkeypatch.setattr(admin, "restart_daemon", lambda: calls.append(("restart_daemon", os.environ.get("BIDI_NAME"))))

    ruyi.main()

    assert ("wait", "127.0.0.1", 12000) in calls
    assert not any(call[0] == "popen" for call in calls)
    assert ("ensure_daemon", "ws://127.0.0.1:12000/session") in calls
    assert calls.index(("ensure_daemon", "ws://127.0.0.1:12000/session")) < calls.index(("run_doctor", "ruyi-test"))
    assert ("restart_daemon", "ruyi-test") in calls


def test_ruyi_firefox_managed_doctor_launches_runtime(monkeypatch, tmp_path):
    calls = []
    fake_process = FakeProcess()

    monkeypatch.setattr(sys, "argv", ["bidi-ruyi-firefox", "--name", "managed-test", "--doctor", "--profile", str(tmp_path)])
    monkeypatch.setattr(ruyi, "_free_port", lambda: 12001)
    monkeypatch.setattr(ruyi, "_default_browser_path", lambda explicit_path=None: "/opt/ruyi/firefox")
    monkeypatch.setattr(ruyi, "_is_executable_available", lambda path: True)
    monkeypatch.setattr(ruyi, "_wait_for_bidi_endpoint", lambda host, port: calls.append(("wait", host, port)))
    monkeypatch.setattr(ruyi, "_resolve_bidi_ws", lambda host, port: "ws://127.0.0.1:12001/session")
    monkeypatch.setattr(
        ruyi.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append(("popen", args[0], kwargs["env"].get("BIDI_NAME"))) or fake_process,
    )
    monkeypatch.setattr(admin, "ensure_daemon", lambda: calls.append(("ensure_daemon", os.environ.get("BIDI_NAME"), os.environ.get("BIDI_WS"))))
    monkeypatch.setattr(admin, "run_doctor", lambda: calls.append(("run_doctor", os.environ.get("BIDI_BROWSER_NAME"))) or 0)
    monkeypatch.setattr(admin, "restart_daemon", lambda: calls.append(("restart_daemon", os.environ.get("BIDI_NAME"))))

    ruyi.main()

    assert calls[0][0] == "popen"
    assert calls[0][1][:4] == ["/opt/ruyi/firefox", "--remote-debugging-port=12001", "--no-remote", "--marionette"]
    assert ("ensure_daemon", "managed-test", "ws://127.0.0.1:12001/session") in calls
    assert ("run_doctor", "firefox") in calls
    assert fake_process.terminated is True
