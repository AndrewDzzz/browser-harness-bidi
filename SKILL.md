---
name: browser-harness-bidi
description: BiDi-first browser control for agents. Use when the user wants WebDriver BiDi, Firefox automation, or cross-browser standard browser control.
---

# browser-harness-BiDi

Use `bidi-harness` or the managed `bidi-firefox` launcher for WebDriver BiDi browser control.

Compatibility note: `browser-harness` is also available in this fork and routes to the same BiDi implementation, so original Browser Harness muscle memory still works while the transport is WebDriver BiDi.

BiDi is the preferred default for Firefox and the future-facing protocol for cross-browser browser agents. It is the standard automation surface this project builds around.

## Fast path

```bash
bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-firefox` starts geckodriver, requests a WebDriver BiDi WebSocket, runs the harness script, and cleans up the managed browser session.

## Manual harness path

```bash
bidi-harness <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Set one of these before using `bidi-harness` directly:

- `BIDI_WS=ws://127.0.0.1:9222/session` for a direct BiDi WebSocket, commonly Firefox remote debugging.
- `BIDI_WEBDRIVER_URL=http://127.0.0.1:9516` for a WebDriver broker such as geckodriver.
- `BIDI_BROWSER_NAME=firefox` or `BIDI_BROWSER_NAME=chrome`.
- `BIDI_CAPABILITIES='{"moz:firefoxOptions":{"args":["-headless"]}}'` for broker-managed Firefox options.



## Interaction skills

If a browser task involves a known mechanic, read the matching file in `interaction-skills/` before inventing a new approach. Available skills include screenshots, tabs, selectors, forms, uploads, dialogs, network, storage/cookies, and viewport.

## Domain skills

Domain skills live under `agent-workspace/domain-skills/` and are disabled unless `BH_DOMAIN_SKILLS=1`. When enabled, `goto_url(url)` may return `domain_skills`; read those files before inventing a site-specific flow.

Good domain skills store durable selectors, URL patterns, loaded states, and auth-wall clues. Never store credentials, private data, or anti-detection guidance.

## Helpers

Prefer visible, user-like actions first:

```python
capture_screenshot()
click_at_xy(x, y)
type_text("text")
press_key("Enter")
scroll(500, 500, dy=600)
```

Use DOM and raw BiDi when coordinates are the wrong tool:

```python
print(js("document.title"))
print(bidi("browsingContext.getTree"))
```

Common functions:

- `new_tab(url="about:blank")`
- `goto_url(url, wait="none")`
- `wait_for_load(timeout=15)`
- `wait_for_element(selector, timeout=10, visible=False)`
- `wait_for_network_idle(timeout=10, idle_ms=500)`
- `page_info()`
- `list_contexts()`
- `switch_context(context_or_dict)`
- `close_context(context=None)`
- `capture_screenshot(path=None, full=False, max_dim=None)`
- `upload_file(selector, path)`
- `http_get(url)`

## BiDi-first design rules

- Think in `browsingContext`, `script`, `input`, `network`, and `log` modules.
- Use raw `bidi("module.command", ...)` for anything helpers do not cover.
- Put task-specific additions in `agent-workspace/agent_helpers.py`.
- Use BiDi browsing context ids and script realms deliberately.
- Do not treat BiDi as stealth. Standard WebDriver automation may expose `navigator.webdriver`.

## Why this matters

For agents that should survive across Firefox, Chrome, WebDriver Grid, and future browser automation infrastructure, BiDi is the protocol to build around.
