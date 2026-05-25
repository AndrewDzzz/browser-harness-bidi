# Interaction skills

Interaction skills are reusable browser mechanics for browser-harness-bidi.

Read these when a task starts to involve a known interaction pattern. They are intentionally bidi-native and should describe `browsingContext`, `script`, `input`, `network`, and helper functions.

Available skills:

- `browser-basics.md` - page state, tabs, screenshots, selectors, viewport, and PDF capture
- `forms-and-input.md` - forms, text input, file uploads, and dialog handling
- `network-and-storage.md` - network events, network idle waits, localStorage, sessionStorage, and cookies

Rules:

- Prefer visible, user-like actions first: screenshot, click, type.
- Use selectors when they are stable and visible.
- Use raw `bidi("module.command", ...)` for missing primitives.
- Do not add anti-detection or bot-evasion guidance here.
