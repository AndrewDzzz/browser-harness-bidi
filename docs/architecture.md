# Architecture

```text
agent Python code
  -> browser_harness_bidi helpers
  -> JSON-line IPC
  -> browser_harness_bidi.daemon
  -> WebDriver BiDi WebSocket
  -> WebDriver-capable browser
```

Core package:

- `src/browser_harness_bidi/bidi.py` - raw WebDriver BiDi WebSocket client
- `src/browser_harness_bidi/daemon.py` - long-lived browser connection and IPC relay
- `src/browser_harness_bidi/helpers.py` - pre-imported browser helpers
- `src/browser_harness_bidi/firefox.py` - managed geckodriver + Firefox launcher
- `src/browser_harness_bidi/admin.py` - daemon lifecycle and diagnostics

Compatibility package:

- `src/browser_harness/` - thin wrappers for the original import path and `browser-harness` CLI

Agent workspace:

- `agent-workspace/agent_helpers.py` - empty extension point for task-specific helpers
- `agent-workspace/domain-skills/` - optional site-specific playbooks

Design constraints:

- Keep the core small enough for an agent to read.
- Prefer raw `bidi("module.command", ...)` before adding a large abstraction.
- Keep task-specific code in `agent-workspace/agent_helpers.py`.
- Do not treat WebDriver BiDi as stealth or anti-detect automation.
