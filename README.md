# Browser-Harness-BiDi

A BiDi-first version of the `browser-use/browser-harness` idea: one thin daemon, one JSON-line IPC channel, and a small set of helpers that an agent can call from Python.

The original browser-harness proved the important shape: a browser harness should be small enough for an agent to understand and editable enough for an agent to repair. This project keeps that shape, but makes **WebDriver BiDi** the center of gravity.

BiDi is the future-facing layer here because it is:

- a W3C browser automation standard, not a Chromium-only DevTools interface;
- native to modern Firefox automation and increasingly supported by Chrome tooling;
- bidirectional by design, with command and event streams over WebSocket;
- compatible with WebDriver infrastructure such as geckodriver, chromedriver, Selenium Grid, and cloud test providers;
- a cleaner long-term abstraction for browser contexts, script realms, input actions, logs, and network events.

This is not an anti-detect browser. Standard WebDriver BiDi may expose `navigator.webdriver` as required by browser automation semantics. The point is standard, cross-browser control, not hiding automation.

## Fork shape

This repository now keeps the original Browser Harness shape instead of being only a separate toy wrapper:

- `src/browser_harness/` exists as a compatibility package for the original import path.
- `browser-harness` exists as a compatibility CLI, but points at the BiDi implementation.
- `src/browser_harness_bidi/` contains the actual WebDriver BiDi transport, daemon, helpers, and Firefox launcher.
- `agent-workspace/` keeps the self-healing helper workflow without vendoring the original CDP implementation.

So the project is intentionally: **Browser Harness, but BiDi-first**.

## Quick start: managed Firefox BiDi

Install editable from this repo:

```bash
uv tool install -e .
# or: pip install -e .
```

Run through a local managed geckodriver + Firefox session:

```bash
bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Useful variants:

```bash
bidi-firefox --headed <<'PY'
new_tab("https://example.com")
print(page_info())
PY

bidi-firefox --privacy-profile <<'PY'
new_tab("https://example.com")
print(js("navigator.webdriver"))
PY
```

`--privacy-profile` enables official Firefox privacy-hardening preferences. It does not hide WebDriver automation.

## Direct BiDi WebSocket

Firefox exposes a direct BiDi endpoint when launched with remote debugging:

```bash
firefox --remote-debugging-port 9222
export BIDI_WS=ws://127.0.0.1:9222/session
```

Then run:

```bash
bidi-harness <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

## WebDriver broker endpoint

Chrome and Firefox can expose a BiDi WebSocket through WebDriver by requesting `webSocketUrl: true`.

ChromeDriver example:

```bash
chromedriver --port=9515
export BIDI_WEBDRIVER_URL=http://127.0.0.1:9515
export BIDI_BROWSER_NAME=chrome
```

GeckoDriver example:

```bash
geckodriver --host 127.0.0.1 --port 9516
export BIDI_WEBDRIVER_URL=http://127.0.0.1:9516
export BIDI_BROWSER_NAME=firefox
export BIDI_CAPABILITIES='{"moz:firefoxOptions":{"args":["-headless"]}}'
```

To attach ChromeDriver to an already-running Chrome debugging port:

```bash
export BIDI_DEBUGGER_ADDRESS=127.0.0.1:9222
```

## Common helpers

```python
new_tab("https://example.com")
goto_url("https://example.com")
wait_for_load()
print(page_info())
print(list_contexts())
click_at_xy(120, 240)
type_text("hello")
press_key("Enter")
print(js("document.title"))
capture_screenshot("/tmp/bidi-shot.png")
```

## Raw BiDi escape hatch

```python
print(bidi("browsingContext.getTree"))
print(bidi("session.status"))
```

## Daemon controls

```bash
bidi-harness --doctor
bidi-firefox --doctor
bidi-harness --reload
bidi-harness --version
```

## Why BiDi over CDP?

CDP is still the deepest interface for Chrome-specific DevTools work. It remains excellent for tracing, profiling, coverage, and advanced Chromium internals.

BiDi wins where the future matters:

```text
CDP  = Chrome's powerful internal DevTools protocol
BiDi = the cross-browser WebDriver standard for automation
```

For a long-lived browser agent platform, the right shape is a BiDi-first interface with protocol-specific backends when needed. Firefox starts naturally with BiDi; Chrome can follow through WebDriver BiDi or fall back to CDP for deep DevTools-only features.

## Architecture

```text
agent Python code
  -> bidi-harness helpers
  -> JSON-line IPC
  -> browser_harness_bidi.daemon
  -> WebDriver BiDi WebSocket
  -> Firefox / Chrome / WebDriver server
```

Core files stay intentionally small:

- `install.md` for setup and connection troubleshooting.
- `SKILL.md` for day-to-day agent usage.
- `src/browser_harness_bidi/` for protected core package code.
- `agent-workspace/agent_helpers.py` for task-specific helper code the agent may edit.

## Upstream note

This project has been aligned with the `AndrewDzzz/Browser-Harness-BiDi` naming and BiDi-first direction. The referenced upstream currently contains only the `# Browser-Harness-BiDi` README title, so this repo provides the working implementation.
