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


## Browser support

Status as of 2026-05-25. WebDriver BiDi support moves quickly, so treat this as the project support matrix rather than a permanent browser guarantee.

| Browser | BiDi status | How this harness connects | Project stance |
|---|---|---|---|
| Firefox Desktop | First-class | `bidi-firefox`, direct `BIDI_WS=ws://127.0.0.1:PORT/session`, or `geckodriver` with `webSocketUrl=true` | Recommended default and best-tested path |
| Chrome Desktop | Supported through ChromeDriver/WebDriver BiDi | `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=chrome`, optionally `BIDI_DEBUGGER_ADDRESS` | Supported, but CDP still has deeper Chrome-only DevTools coverage |
| Chromium Desktop | Supported through Chromium/ChromeDriver-compatible WebDriver BiDi stacks | `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=chrome` or browser-specific capabilities | Expected to work when the driver returns `webSocketUrl`; less tested than Firefox |
| Microsoft Edge Desktop | Expected via EdgeDriver/WebDriver BiDi because Edge is Chromium-based, but not verified in this repo yet | `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=edge` with Edge capabilities | Experimental until we add an Edge smoke test |
| Safari / safaridriver | Not a supported target for this harness today | None | Track WebKit/Safari progress; do not promise support yet |
| Mobile browsers | Not supported by this harness today | None | Future work; likely requires Appium/cloud-provider-specific BiDi support |

Important nuance:

- MDN documents two connection shapes: `webSocketUrl=true` during WebDriver session creation, and a direct browser WebSocket; the direct command-line flow works with Firefox, while Chromium-based browsers need the Chromium BiDi wrapper path. See [MDN: Create a WebDriver BiDi connection](https://developer.mozilla.org/en-US/docs/Web/WebDriver/How_to/Create_BiDi_connection).
- MDN documents the `webSocketUrl` capability: setting it to `true` asks the browser/driver to start a WebSocket server for WebDriver BiDi. See [MDN: webSocketUrl](https://developer.mozilla.org/en-US/docs/Web/WebDriver/Reference/Capabilities/webSocketUrl).
- ChromeDriver officially implements both W3C WebDriver and WebDriver BiDi standards, and is available for desktop Chrome and Chrome on Android. See [ChromeDriver docs](https://developer.chrome.com/docs/chromedriver?hl=en).
- Puppeteer documents WebDriver BiDi automation with Chrome and Firefox, but also notes Chrome still defaults to CDP because not every CDP feature is supported over BiDi yet. See [Puppeteer WebDriver BiDi support](https://pptr.dev/webdriver-bidi).
- Safari/WebKit BiDi support is still not a project target here. WebKit has active BiDi tracking work, but this harness should not advertise Safari support until there is a stable, tested path. See [WebKit BiDi meta bug](https://www2.webkit.org/show_bug.cgi?id=281932).

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



## Interaction skills

Reusable BiDi interaction notes live in `interaction-skills/`. They cover browser mechanics such as screenshots, tabs, selectors, forms, uploads, dialogs, network events, storage/cookies, and viewport/PDF work.

These files are intentionally BiDi-native. They should describe `browsingContext`, `script`, `input`, `network`, and helper functions rather than CDP domains. Agents should read the relevant interaction skill before adding one-off helper code.

## Domain skills

Browser-Harness-BiDi includes an optional `agent-workspace/domain-skills/` directory for site-specific playbooks. This keeps the original Browser Harness self-healing idea without vendoring CDP-specific skills.

Enable domain skill hints with:

```bash
export BH_DOMAIN_SKILLS=1
```

When enabled, `goto_url(url)` returns a `domain_skills` field listing matching Markdown files for the current site, for example `agent-workspace/domain-skills/github/repository-basics.md`. Agents should read those files before inventing a site flow.

Domain skills should contain durable URL patterns, selectors, page states, and workflow notes. They must not contain credentials, private data, or anti-detection guidance.

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
