import os
import sys

import browser_harness_bidi.admin as admin
import browser_harness_bidi.chrome as chrome


class FakeProcess:
    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


def _parse(args):
    parsed = chrome._parser().parse_args(args)
    parsed.headless = not parsed.headed
    return parsed


def test_chrome_capabilities_build_chrome_options():
    args = _parse(
        [
            "--chrome-binary",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--user-data-dir",
            "~/chrome-profile",
            "--profile-directory",
            "Profile 1",
            "--proxy-server",
            "http://127.0.0.1:8080",
            "--window-size",
            "1280x720",
            "--argument",
            "disable-gpu",
            "--capabilities",
            '{"acceptInsecureCerts": true, "goog:chromeOptions": {"prefs": {"download.default_directory": "/tmp/dl"}}}',
        ]
    )

    caps = chrome._build_capabilities(args)

    options = caps["goog:chromeOptions"]
    assert caps["acceptInsecureCerts"] is True
    assert options["binary"].endswith("/Google Chrome")
    assert "--headless=new" in options["args"]
    assert "--user-data-dir=~/chrome-profile" not in options["args"]
    assert any(arg.startswith("--user-data-dir=") and "chrome-profile" in arg for arg in options["args"])
    assert "--profile-directory=Profile 1" in options["args"]
    assert "--proxy-server=http://127.0.0.1:8080" in options["args"]
    assert "--window-size=1280,720" in options["args"]
    assert "--disable-gpu" in options["args"]
    assert options["prefs"] == {"download.default_directory": "/tmp/dl"}


def test_chrome_debugger_address_uses_attach_capability():
    args = _parse(["--debugger-address", "127.0.0.1:9222", "--user-data-dir", "~/ignored"])

    assert chrome._build_capabilities(args) == {
        "goog:chromeOptions": {"debuggerAddress": "127.0.0.1:9222"}
    }


def test_chrome_doctor_starts_daemon_before_doctor(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["bidi-chrome", "--name", "doctor-test", "--doctor"])
    monkeypatch.setattr(chrome, "_free_port", lambda: 45679)
    monkeypatch.setattr(chrome, "_wait_for_driver", lambda port: calls.append(("wait", port)))
    monkeypatch.setattr(chrome.shutil, "which", lambda name: "/usr/bin/chromedriver")
    monkeypatch.setattr(
        chrome.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append(("popen", args[0], kwargs["env"].get("BIDI_BROWSER_NAME"))) or FakeProcess(),
    )
    monkeypatch.setattr(admin, "ensure_daemon", lambda: calls.append(("ensure_daemon", os.environ.get("BIDI_NAME"))))
    monkeypatch.setattr(admin, "run_doctor", lambda: calls.append(("run_doctor", os.environ.get("BIDI_NAME"))) or 0)
    monkeypatch.setattr(admin, "restart_daemon", lambda: calls.append(("restart_daemon", os.environ.get("BIDI_NAME"))))

    chrome.main()

    assert ("wait", 45679) in calls
    assert ("popen", ["chromedriver", "--port=45679"], "chrome") in calls
    assert calls.index(("ensure_daemon", "doctor-test")) < calls.index(("run_doctor", "doctor-test"))
    assert ("restart_daemon", "doctor-test") in calls
