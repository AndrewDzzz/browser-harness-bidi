# browser-harness-bidi ♞

Connect an LLM directly to a real browser with a thin, editable **WebDriver bidi** harness.

One WebSocket to a WebDriver-capable browser, one tiny daemon, one editable helper workspace. The agent writes what is missing during execution. The harness improves itself every run.

```text
  * agent: needs browser state or an action
  |
  * browser-harness-bidi helpers
  |
  * WebDriver bidi WebSocket
  |
  * WebDriver-capable browser
      - Firefox via geckodriver
      - Chrome via ChromeDriver bidi
  |
  ✓ page inspected, clicked, typed, extracted, or captured
```

When a task needs a reusable helper that does not belong in the core package, the agent can add it to `agent-workspace/agent_helpers.py` and use it in the next run.

**bidi is not a stealth layer. It is the standard automation layer.** Standard WebDriver bidi may expose `navigator.webdriver`. This project is about correct, future-facing browser control, not hiding automation.

## Setup prompt

Paste into Codex or Claude Code:

```text
Set up https://github.com/AndrewDzzz/browser-harness-bidi for me.

Read `install.md` and follow the steps to install browser-harness-bidi and run the managed Firefox bidi smoke test.
```

## Quick start

```bash
uv tool install -e .

bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-firefox` starts geckodriver, requests a WebDriver bidi WebSocket, runs your script, and shuts the managed session down.

Chrome can use the same helper surface through ChromeDriver:

```bash
bidi-chrome <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-chrome` starts chromedriver, requests a Chrome WebDriver bidi WebSocket, runs your script, and shuts the managed session down.

## Why bidi

The original `browser-use/browser-harness` proved the important shape: a browser harness should be small enough for an agent to understand and editable enough for an agent to repair. This project keeps that shape, but makes **WebDriver bidi** the center of gravity.

bidi is the future-facing layer because it is:

- a W3C browser automation standard;
- native to modern Firefox automation and increasingly supported by Chrome tooling;
- bidirectional by design, with command and event streams over WebSocket;
- compatible with WebDriver infrastructure such as geckodriver, chromedriver, Selenium Grid, and cloud test providers;
- a clean abstraction for browser contexts, script realms, input actions, logs, and network events.

```text
bidi = the cross-browser WebDriver standard for automation
```

## Architecture

- `install.md` - first-time install and browser bootstrap
- `SKILL.md` - day-to-day agent usage
- `src/browser_harness_bidi/` - protected bidi core package
- `src/browser_harness/` - compatibility wrapper for the original import path and CLI
- `agent-workspace/agent_helpers.py` - helper code the agent edits
- `agent-workspace/domain-skills/` - optional reusable site-specific skills
- `interaction-skills/` - reusable bidi interaction mechanics
- `tests/unit/` - fast unit tests for helper behavior

More detail: [docs/architecture.md](docs/architecture.md)

## What actually works

- Managed Firefox: `bidi-firefox <<'PY' ... PY` starts geckodriver and Firefox for you.
- Managed Chrome: `bidi-chrome <<'PY' ... PY` starts chromedriver and Chrome for you.
- Manual bidi: set `BIDI_WS` or `BIDI_WEBDRIVER_URL` and use `bidi-harness`.
- Navigation and tabs: `new_tab()`, `goto_url()`, `reload()`, `list_tabs()`, `switch_tab()`, `ensure_real_tab()`.
- Screenshots and PDFs: `capture_screenshot()`, `print_pdf()`.
- JavaScript and raw protocol: `js(expression)`, `bidi("module.command", ...)`.
- Input and selectors: `click_at_xy()`, `click_selector()`, `type_text()`, `press_key()`, `fill_input()`, `wait_for_element()`, `get_text()`.
- Storage and cookies: simple same-origin localStorage, sessionStorage, and document cookie helpers.
- Network observation: `network_events()`, `capture_network_during()`, `summarize_network()`, `wait_for_network_idle()`.

## Browser support

Firefox Desktop is the first-class path. Chrome and Chromium are supported through ChromeDriver/WebDriver bidi when the driver returns a `webSocketUrl`. Edge is experimental. Safari and mobile browsers are not supported by this harness today.

Full matrix: [docs/browser-support.md](docs/browser-support.md)

## Connection modes

See [docs/connection.md](docs/connection.md) for managed Firefox, direct Firefox bidi WebSocket, geckodriver, and ChromeDriver setup.

## Interaction skills

Reusable bidi interaction notes live in `interaction-skills/`:

- `browser-basics.md`
- `forms-and-input.md`
- `network-and-storage.md`

Agents should read the relevant interaction skill before adding one-off helper code.

## Domain skills

Set `BH_DOMAIN_SKILLS=1` to enable `agent-workspace/domain-skills/`. These are optional per-site playbooks surfaced by `goto_url(url)`.

Domain skills should contain durable URL patterns, selectors, page states, and workflow notes. They must not contain credentials, private data, or anti-detection guidance.

## Contributors

- [AndrewDzzz](https://github.com/AndrewDzzz) - project owner and maintainer.
- Codex - implementation, documentation, and bidi harness iteration partner.

## Contributing

PRs and improvements welcome. The best way to help is to make bidi boringly useful:

- add unit tests for helper behavior under `tests/unit/`;
- improve Firefox and ChromeDriver smoke coverage;
- add bidi-native interaction skills;
- contribute small, focused domain skills under `agent-workspace/domain-skills/<site>/`;
- keep `agent-workspace/agent_helpers.py` as the empty extension point agents edit during real tasks.

Prefer small patches. If a helper is missing, first prove it can be expressed with raw `bidi("module.command", ...)`, then wrap it only if it is broadly reusable.

## Upstream note

browser-harness-bidi is inspired by the architecture and workflow of [browser-use/browser-harness](https://github.com/browser-use/browser-harness), licensed under MIT. It reimplements the transport and helper layer around WebDriver bidi while preserving a compatible, small-harness workflow for agents.
