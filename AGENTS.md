Browser-Harness-BiDi is a thin layer that connects agents to browsers through an editable WebDriver BiDi harness.

# Code priorities

- Clarity
- Precision
- Low verbosity
- Versatility
- BiDi-first semantics

# Overview

Core code lives in `src/bidi_harness/`:

- `admin.py` - daemon lifecycle and diagnostics
- `daemon.py` - the long-lived middleman process between the browser and the agent
- `bidi.py` - the raw WebDriver BiDi WebSocket client
- `helpers.py` - BiDi wrapper and core browser primitives auto-imported into scripts
- `firefox.py` - managed geckodriver + Firefox launcher
- `run.py` - the `bidi-harness` / compatibility CLI

Compatibility wrappers live in `src/browser_harness/` so code written for the original package name can still import this fork.

`SKILL.md` tells agents how to use the harness and CLI.
`install.md` tells agents how to install it, attach a browser, and troubleshoot.

An agent operating the harness should usually edit only inside `agent-workspace/`:

- `agent_helpers.py` - task-specific browser helpers the agent adds
- `domain-skills/` - optional site-specific skills the agent writes and reads

# Contributing

Prefer the smallest diff that fixes the bug. Keep the core small enough for an agent to read. Use raw `bidi("module.command", ...)` before adding a large abstraction.

# Protocol stance

CDP is a powerful Chromium DevTools interface. BiDi is the cross-browser WebDriver standard and the future-facing automation surface. This fork should make that future practical without pretending BiDi is stealth or anti-detect.
