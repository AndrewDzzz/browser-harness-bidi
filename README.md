# browser-harness-bidi ♞

Connect an LLM directly to a real browser with a thin, editable **WebDriver BiDi** harness.

One WebSocket to a WebDriver-capable browser, one tiny daemon, one editable helper workspace. The agent writes what is missing during execution. The harness improves itself every run.

```text
  * agent: needs browser state or an action
  |
  * browser-harness-bidi helpers
  |
  * WebDriver BiDi WebSocket
  |
  * WebDriver-capable browser
      - Firefox via geckodriver
      - ruyiPage-compatible Firefox via direct Firefox Remote Agent
      - Chrome via ChromeDriver BiDi
  |
  ✓ page inspected, clicked, typed, extracted, or captured
```

When a task needs a reusable helper that does not belong in the core package, the agent can add it to `agent-workspace/agent_helpers.py` and use it in the next run.

**BiDi is not a stealth layer. It is the standard automation layer.** Standard WebDriver BiDi may expose `navigator.webdriver`. This project is about correct, future-facing browser control, not hiding automation.

## Setup prompt

Paste into Codex or Claude Code:

```text
Set up https://github.com/AndrewDzzz/browser-harness-bidi for me.

Read `install.md` and follow the steps to install browser-harness-bidi and run the managed Firefox BiDi smoke test.
```

## Quick start

```bash
uv tool install -e .
```

Pick the launcher that matches the browser path you want:

| Command | Browser path | Transport |
|---|---|---|
| `bidi-firefox` | Stock Firefox through geckodriver | WebDriver broker requests `webSocketUrl=true` |
| `bidi-ruyi-firefox` | ruyiPage Firefox runtime or compatible Firefox build | Direct Firefox Remote Agent / WebDriver BiDi socket |
| `bidi-chrome` | Chrome or Chromium through ChromeDriver | WebDriver broker requests `webSocketUrl=true` |
| `bidi-harness` | Bring your own endpoint | Uses `BIDI_WS` or `BIDI_WEBDRIVER_URL` |

Managed Firefox:

```bash
bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-firefox` starts geckodriver, requests a WebDriver BiDi WebSocket, runs your script, and shuts the managed session down.

ruyiPage-compatible Firefox:

```bash
bidi-ruyi-firefox --browser-path /path/to/firefox --fpfile /path/to/fpfile.txt <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-ruyi-firefox` starts Firefox with `--remote-debugging-port`, resolves the direct WebDriver BiDi socket, runs your script, and shuts the managed browser down.

Managed Chrome:

```bash
bidi-chrome <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-chrome` starts chromedriver, requests a Chrome WebDriver BiDi WebSocket, runs your script, and shuts the managed session down.

## ruyiPage Firefox

`bidi-ruyi-firefox` is the adapter for ruyiPage-style Firefox automation. It does not import or wrap the ruyiPage page API. Instead, it uses the same underlying route: Firefox exposes WebDriver BiDi directly through its Remote Agent.

Use it when:

- you installed ruyiPage's managed Firefox runtime;
- you have a custom Firefox runtime that accepts `--remote-debugging-port`;
- you need to pass a ruyiPage/firefox-fingerprintBrowser-style `--fpfile`;
- you want this harness's small helper API on top of a direct Firefox BiDi endpoint.

If ruyiPage is installed, `bidi-ruyi-firefox` will try `ruyipage.resolve_firefox_path()` before falling back to system Firefox. You can always be explicit:

```bash
bidi-ruyi-firefox \
  --browser-path /path/to/firefox \
  --user-dir "$HOME/ruyi-bidi-profile" \
  --fpfile "$HOME/fpfile.txt" <<'PY'
print(page_info())
PY
```

Attach to an already-open Firefox Remote Agent endpoint:

```bash
bidi-ruyi-firefox --existing-address 127.0.0.1:12000 <<'PY'
print(list_tabs())
PY
```

If another ruyiPage process already owns the active BiDi session, the attach flow can fail when the harness sends `session.new`. In that case, start a separate browser with `bidi-ruyi-firefox`, close the owning ruyiPage driver first, or connect to an already-created session WebSocket with `--bidi-ws ... --session-ready`.

## Why BiDi

The original `browser-use/browser-harness` proved the important shape: a browser harness should be small enough for an agent to understand and editable enough for an agent to repair. This project keeps that shape, but makes **WebDriver BiDi** the center of gravity.

BiDi is the future-facing layer because it is:

- a W3C browser automation standard;
- native to modern Firefox automation and increasingly supported by Chrome tooling;
- bidirectional by design, with command and event streams over WebSocket;
- compatible with WebDriver infrastructure such as geckodriver, chromedriver, Selenium Grid, and cloud test providers;
- a clean abstraction for browser contexts, script realms, input actions, logs, and network events.

```text
BiDi = the cross-browser WebDriver standard for automation
```

## Architecture

- `install.md` - first-time install and browser bootstrap
- `SKILL.md` - day-to-day agent usage
- `src/browser_harness_bidi/` - protected BiDi core package
- `src/browser_harness/` - compatibility wrapper for the original import path and CLI
- `agent-workspace/agent_helpers.py` - helper code the agent edits
- `agent-workspace/domain-skills/` - optional reusable site-specific skills
- `interaction-skills/` - reusable BiDi interaction mechanics
- `tests/unit/` - fast unit tests for helper behavior

More detail: [docs/architecture.md](docs/architecture.md)

## What actually works

- Managed Firefox: `bidi-firefox <<'PY' ... PY` starts geckodriver and Firefox for you.
- ruyiPage-compatible Firefox: `bidi-ruyi-firefox <<'PY' ... PY` starts or attaches to a direct Firefox BiDi endpoint.
- Managed Chrome: `bidi-chrome <<'PY' ... PY` starts chromedriver and Chrome for you.
- Manual BiDi: set `BIDI_WS` or `BIDI_WEBDRIVER_URL` and use `bidi-harness`.
- Navigation and tabs: `new_tab()`, `goto_url()`, `reload()`, `list_tabs()`, `switch_tab()`, `ensure_real_tab()`.
- Screenshots and PDFs: `capture_screenshot()`, `print_pdf()`.
- JavaScript and raw protocol: `js(expression)`, `bidi("module.command", ...)`.
- Input and selectors: `click_at_xy()`, `click_selector()`, `type_text()`, `press_key()`, `fill_input()`, `wait_for_element()`, `get_text()`.
- Storage and cookies: simple same-origin localStorage, sessionStorage, and document cookie helpers.
- Network observation: `network_events()`, `capture_network_during()`, `summarize_network()`, `wait_for_network_idle()`.

## Browser support

Firefox Desktop is the first-class path. Chrome and Chromium are supported through ChromeDriver/WebDriver BiDi when the driver returns a `webSocketUrl`. Edge is experimental. Safari and mobile browsers are not supported by this harness today.

Full matrix: [docs/browser-support.md](docs/browser-support.md)

## Connection modes

See [docs/connection.md](docs/connection.md) for managed Firefox, ruyiPage-compatible Firefox, direct Firefox BiDi WebSocket, geckodriver, and ChromeDriver setup.

## Interaction skills

Reusable BiDi interaction notes live in `interaction-skills/`:

- `browser-basics.md`
- `forms-and-input.md`
- `network-and-storage.md`

Agents should read the relevant interaction skill before adding one-off helper code.

## Domain skills

Set `BH_DOMAIN_SKILLS=1` to enable `agent-workspace/domain-skills/`. These are optional per-site playbooks surfaced by `goto_url(url)`.

Domain skills should contain durable URL patterns, selectors, page states, and workflow notes. They must not contain credentials, private data, or anti-detection guidance.

## Contributors

- [AndrewDzzz](https://github.com/AndrewDzzz) - project owner and maintainer.
- Codex - implementation, documentation, and BiDi harness iteration partner.

## Contributing

PRs and improvements welcome. The best way to help is to make BiDi boringly useful:

- add unit tests for helper behavior under `tests/unit/`;
- improve Firefox and ChromeDriver smoke coverage;
- add BiDi-native interaction skills;
- contribute small, focused domain skills under `agent-workspace/domain-skills/<site>/`;
- keep `agent-workspace/agent_helpers.py` as the empty extension point agents edit during real tasks.

Prefer small patches. If a helper is missing, first prove it can be expressed with raw `bidi("module.command", ...)`, then wrap it only if it is broadly reusable.

## Upstream note

browser-harness-bidi is inspired by the architecture and workflow of [browser-use/browser-harness](https://github.com/browser-use/browser-harness), licensed under MIT. It reimplements the transport and helper layer around WebDriver BiDi while preserving a compatible, small-harness workflow for agents.
