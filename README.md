# Browser-Harness-BiDi ♞

Connect an LLM directly to a real browser with a thin, editable **WebDriver BiDi** harness. For browser tasks where you want the Browser Harness workflow on the cross-browser automation standard.

One WebSocket to a WebDriver BiDi browser, one tiny daemon, one editable helper workspace. The agent writes what is missing during execution. The harness improves itself every run.

```text
  * agent: wants to operate a Firefox page
  |
  * browser-harness-bidi -> WebDriver BiDi -> Firefox / Chrome driver
  |
  * agent-workspace/agent_helpers.py -> helper missing
  |                                      + custom helper
  |
  ✓ task completed
```

**BiDi is not a stealth layer. It is the standard automation layer.** Standard WebDriver BiDi may expose `navigator.webdriver`. This project is about correct, future-facing browser control, not hiding automation.

## Setup prompt

Paste into Codex or Claude Code:

```text
Set up https://github.com/AndrewDzzz/Browser-Harness-BiDi for me.

Read `install.md` and follow the steps to install Browser-Harness-BiDi and run the managed Firefox BiDi smoke test.
```

The fastest local path is managed Firefox:

```bash
uv tool install -e .

bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-firefox` starts geckodriver, requests a WebDriver BiDi WebSocket, runs your script, and shuts the managed session down.

## Why BiDi

The original `browser-use/browser-harness` proved the important shape: a browser harness should be small enough for an agent to understand and editable enough for an agent to repair. This project keeps that shape, but makes **WebDriver BiDi** the center of gravity.

BiDi is the future-facing layer because it is:

- a W3C browser automation standard;
- native to modern Firefox automation and increasingly supported by Chrome tooling;
- bidirectional by design, with command and event streams over WebSocket;
- compatible with WebDriver infrastructure such as geckodriver, chromedriver, Selenium Grid, and cloud test providers;
- a cleaner long-term abstraction for browser contexts, script realms, input actions, logs, and network events.

Browser-Harness-BiDi focuses entirely on the BiDi path:

```text
BiDi = the cross-browser WebDriver standard for automation
```

## Architecture (~2.4k lines including docs and tests)

- `install.md` - first-time install and browser bootstrap
- `SKILL.md` - day-to-day agent usage
- `src/browser_harness_bidi/` - protected BiDi core package
- `src/browser_harness/` - compatibility wrapper for the original import path and CLI
- `agent-workspace/agent_helpers.py` - helper code the agent edits
- `agent-workspace/domain-skills/` - optional reusable site-specific skills
- `interaction-skills/` - reusable BiDi interaction mechanics
- `tests/unit/` - fast unit tests for helper behavior

Compatibility is intentional: `browser-harness`, `browser-harness-bidi`, `bidi-harness`, and `bidi-firefox` are all available entry points.

## What actually works

- Managed Firefox: `bidi-firefox <<'PY' ... PY` starts geckodriver and Firefox for you.
- Manual BiDi: set `BIDI_WS` or `BIDI_WEBDRIVER_URL` and use `bidi-harness`.
- Navigation: `new_tab(url)`, `goto_url(url)`, `reload()`, `back()`, `forward()`.
- Contexts and tabs: `list_tabs()`, `switch_tab()`, `ensure_real_tab()`, `close_tab()`.
- Screenshots: `capture_screenshot()`, full-page screenshots, max-dimension thumbnails.
- JavaScript: `js(expression)` and raw `bidi("module.command", ...)`.
- Input: `click_at_xy()`, `click_selector()`, `type_text()`, `press_key()`, `fill_input()`.
- Selectors: `wait_for_element()`, `element_rect()`, `get_text()`, `get_html()`, `get_value()`, `get_attr()`, `count()`, `exists()`.
- Storage/cookies: simple same-origin localStorage, sessionStorage, and cookie helpers.
- Dialogs: `page_info()` surfaces pending prompts; `handle_prompt()` accepts/dismisses.
- Viewport/PDF: `set_viewport()` and `print_pdf()` when the browser supports BiDi print.
- Network: common BiDi network events are buffered; `network_events()`, `capture_network_during()`, `summarize_network()`, and `wait_for_network_idle()` cover request/response observation.

## Browser support

Status as of 2026-05-25. WebDriver BiDi support moves quickly, so treat this as the project support matrix rather than a permanent browser guarantee.

| Browser | BiDi status | How this harness connects | Project stance |
|---|---|---|---|
| Firefox Desktop | First-class | `bidi-firefox`, direct `BIDI_WS=ws://127.0.0.1:PORT/session`, or `geckodriver` with `webSocketUrl=true` | Recommended default and best-tested path |
| Chrome Desktop | Supported through ChromeDriver/WebDriver BiDi | `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=chrome` | Supported through the WebDriver BiDi path |
| Chromium Desktop | Supported through Chromium/ChromeDriver-compatible WebDriver BiDi stacks | `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=chrome` or browser-specific capabilities | Expected to work when the driver returns `webSocketUrl`; less tested than Firefox |
| Microsoft Edge Desktop | Expected via EdgeDriver/WebDriver BiDi because Edge is Chromium-based, but not verified in this repo yet | `BIDI_WEBDRIVER_URL` + `BIDI_BROWSER_NAME=edge` with Edge capabilities | Experimental until we add an Edge smoke test |
| Safari / safaridriver | Not a supported target for this harness today | None | Track WebKit/Safari progress; do not promise support yet |
| Mobile browsers | Not supported by this harness today | None | Future work; likely requires Appium/cloud-provider-specific BiDi support |

Important references:

- [MDN: Create a WebDriver BiDi connection](https://developer.mozilla.org/en-US/docs/Web/WebDriver/How_to/Create_BiDi_connection)
- [MDN: webSocketUrl capability](https://developer.mozilla.org/en-US/docs/Web/WebDriver/Reference/Capabilities/webSocketUrl)
- [ChromeDriver docs](https://developer.chrome.com/docs/chromedriver?hl=en)
- [Puppeteer WebDriver BiDi support](https://pptr.dev/webdriver-bidi)
- [WebKit BiDi meta bug](https://www2.webkit.org/show_bug.cgi?id=281932)

## Connection modes

### Managed Firefox

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

Use official Firefox privacy-hardening preferences:

```bash
bidi-firefox --privacy-profile <<'PY'
new_tab("https://example.com")
print(js("navigator.webdriver"))
PY
```

`--privacy-profile` is a privacy profile, not an anti-detect profile.

### Direct Firefox BiDi WebSocket

```bash
firefox --remote-debugging-port 9222
export BIDI_WS=ws://127.0.0.1:9222/session

bidi-harness <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

### WebDriver broker endpoint

Chrome and Firefox can expose a BiDi WebSocket through WebDriver by requesting `webSocketUrl: true`.

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

## Tool call shape

Use heredocs for multi-line browser work. Helpers are pre-imported and the daemon auto-starts.

```bash
bidi-harness <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
print(capture_screenshot())
PY
```

Raw BiDi is always available:

```python
print(bidi("browsingContext.getTree"))
print(bidi("session.status"))
```

Daemon controls:

```bash
bidi-harness --doctor
bidi-firefox --doctor
bidi-harness --reload
bidi-harness --version
```

## Interaction skills

Reusable BiDi interaction notes live in `interaction-skills/`. They cover browser mechanics such as screenshots, tabs, selectors, forms, uploads, dialogs, network events, storage/cookies, and viewport/PDF work.

Agents should read the relevant interaction skill before adding one-off helper code. The files are BiDi-native and should describe `browsingContext`, `script`, `input`, `network`, and helper functions.

## Domain skills

Set `BH_DOMAIN_SKILLS=1` to enable `agent-workspace/domain-skills/`. These are optional per-site playbooks surfaced by `goto_url(url)`.

```bash
export BH_DOMAIN_SKILLS=1
```

When enabled, `goto_url("https://github.com/AndrewDzzz/Browser-Harness-BiDi")` may return:

```python
{"domain_skills": ["repository-basics.md"]}
```

Domain skills should contain durable URL patterns, selectors, page states, and workflow notes. They must not contain credentials, private data, or anti-detection guidance.

## Contributing

PRs and improvements welcome. The best way to help is to make BiDi boringly useful:

- add unit tests for helper behavior under `tests/unit/`;
- improve Firefox and ChromeDriver smoke coverage;
- add BiDi-native interaction skills;
- contribute small, focused domain skills under `agent-workspace/domain-skills/<site>/`;
- keep `agent-workspace/agent_helpers.py` as the empty extension point agents edit during real tasks.

Prefer small patches. If a helper is missing, first prove it can be expressed with raw `bidi("module.command", ...)`, then wrap it only if it is broadly reusable.

## Upstream note

Browser-Harness-BiDi is inspired by the architecture and workflow of [browser-use/browser-harness](https://github.com/browser-use/browser-harness), licensed under MIT. It reimplements the transport and helper layer around WebDriver BiDi while preserving a compatible, small-harness workflow for agents.
