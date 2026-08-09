# browser-harness-bidi installation and connection

Use this file for setup, install, and connection troubleshooting. Day-to-day usage belongs in `SKILL.md`.

Full environment-variable reference: `docs/env-vars.md`.

## Install

```bash
uv tool install -e .
command -v browser-harness
command -v browser-harness-bidi
command -v bidi-harness
command -v bidi-firefox
command -v bidi-chrome
```

Or, inside a development environment:

```bash
pip install -e .
```

## Recommended: managed Firefox bidi

The easiest local path is `bidi-firefox`. It starts geckodriver, requests a WebDriver bidi WebSocket, runs your harness script, then shuts the managed session down.

```bash
bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Show the browser:

```bash
bidi-firefox --headed <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

Use a named daemon namespace:

```bash
bidi-firefox --name research <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

Use official Firefox privacy-hardening preferences:

```bash
bidi-firefox --privacy-profile <<'PY'
new_tab("https://example.com")
print(js("navigator.webdriver"))
PY
```

This is a privacy profile, not an anti-detect profile. WebDriver automation may still be visible to pages.

## Managed Chrome bidi

Use `bidi-chrome` when you want the same harness helpers through ChromeDriver. It starts chromedriver, asks it for a WebDriver BiDi `webSocketUrl`, then connects the daemon to that socket.

```bash
bidi-chrome <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Show the browser:

```bash
bidi-chrome --headed <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

Use a specific Chrome binary or profile:

```bash
bidi-chrome \
  --chrome-binary "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir "$HOME/chrome-bidi-profile" \
  --profile-directory "Default" <<'PY'
print(page_info())
PY
```

Attach ChromeDriver to an already-running Chrome debug address:

```bash
bidi-chrome --debugger-address 127.0.0.1:9222 <<'PY'
print(list_tabs())
PY
```

This is the standard ChromeDriver/WebDriver BiDi route, not a CDP stealth route. ChromeDriver must be installed and compatible with the Chrome version you launch.

## Manual connection modes

### Mode 1: direct bidi WebSocket

Set `BIDI_WS` to a WebDriver bidi WebSocket endpoint.

Firefox example:

```bash
firefox --remote-debugging-port 9222
export BIDI_WS=ws://127.0.0.1:9222/session
```

The harness will connect to the WebSocket and create a bidi session with `session.new`.

If your `BIDI_WS` already points to an existing session WebSocket returned by a WebDriver New Session response, set:

```bash
export BIDI_SESSION_READY=1
```

### Mode 2: WebDriver broker endpoint

Set `BIDI_WEBDRIVER_URL` to a WebDriver server root URL. The harness will create a classic WebDriver session with `webSocketUrl: true`, read the returned bidi WebSocket URL, and connect to it.

Firefox example:

```bash
geckodriver --host 127.0.0.1 --port 9516
export BIDI_WEBDRIVER_URL=http://127.0.0.1:9516
export BIDI_BROWSER_NAME=firefox
export BIDI_CAPABILITIES='{"moz:firefoxOptions":{"args":["-headless"]}}'
```

ChromeDriver example:

```bash
chromedriver --port=9515
export BIDI_WEBDRIVER_URL=http://127.0.0.1:9515
export BIDI_BROWSER_NAME=chrome
```


Extra capabilities can be merged with JSON:

```bash
export BIDI_CAPABILITIES='{"acceptInsecureCerts":true}'
```

By default the harness does not DELETE the classic WebDriver session on daemon shutdown, because doing so can close a browser that the user cares about. Opt in with:

```bash
export BIDI_DELETE_WEBDRIVER_SESSION=1
```

## Architecture

```text
Browser / WebDriver server -> WebDriver bidi WS -> browser_harness_bidi.daemon -> IPC -> browser_harness_bidi.run
```

- Protocol to the browser is WebDriver bidi JSON over WebSocket.
- Protocol between CLI and daemon is one JSON line each way.
- IPC is an AF_UNIX socket on POSIX and TCP loopback with a token on Windows.
- `BIDI_NAME` namespaces daemon runtime files.
- `BH_AGENT_WORKSPACE` points to editable helper code; defaults to `agent-workspace/` in this repo.

## First smoke test

```bash
bidi-firefox <<'PY'
print(page_info())
PY
```

If it fails, run:

```bash
bidi-firefox --doctor
bidi-harness --doctor
```

The most common failure is no endpoint configured for `bidi-harness`, or no `geckodriver` binary available for `bidi-firefox`.
