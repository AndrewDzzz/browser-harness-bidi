import os
import sys

import browser_harness_bidi.admin as admin
import browser_harness_bidi.firefox as firefox


class FakeProcess:
    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


def test_firefox_doctor_starts_daemon_before_doctor(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(sys, "argv", ["bidi-firefox", "--name", "doctor-test", "--doctor"])
    monkeypatch.setattr(firefox, "_free_port", lambda: 45678)
    monkeypatch.setattr(firefox, "_wait_for_driver", lambda port: calls.append(("wait", port)))
    monkeypatch.setattr(firefox.shutil, "which", lambda name: "/usr/bin/geckodriver")
    monkeypatch.setattr(
        firefox.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append(("popen", args[0])) or FakeProcess(),
    )
    monkeypatch.setattr(admin, "ensure_daemon", lambda: calls.append(("ensure_daemon", os.environ.get("BIDI_NAME"))))
    monkeypatch.setattr(admin, "run_doctor", lambda: calls.append(("run_doctor", os.environ.get("BIDI_NAME"))) or 0)
    monkeypatch.setattr(admin, "restart_daemon", lambda: calls.append(("restart_daemon", os.environ.get("BIDI_NAME"))))

    firefox.main()

    assert ("wait", 45678) in calls
    assert calls.index(("ensure_daemon", "doctor-test")) < calls.index(("run_doctor", "doctor-test"))
    assert ("restart_daemon", "doctor-test") in calls
