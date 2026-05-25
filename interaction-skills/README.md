# Interaction skills

Interaction skills are reusable browser mechanics for Browser-Harness-BiDi.

Read these when a task starts to involve a known interaction pattern. They are intentionally BiDi-native and should not assume CDP domains such as `Page`, `Runtime`, `Target`, or `Input.dispatchMouseEvent`.

Available skills:

- `screenshots.md` - inspect page state visually
- `tabs.md` - create, switch, and close browsing contexts
- `selectors.md` - use selector helpers without overfitting to DOM
- `forms.md` - fill inputs and submit framework-managed forms
- `uploads.md` - set files on file inputs
- `dialogs.md` - handle alert/confirm/prompt dialogs
- `network.md` - use network events and network idle waits
- `storage-cookies.md` - read/write localStorage, sessionStorage, and simple cookies
- `viewport.md` - viewport sizing and screenshots/PDF

Rules:

- Prefer visible, user-like actions first: screenshot, click, type.
- Use selectors when they are stable and visible.
- Use raw `bidi("module.command", ...)` for missing primitives.
- Do not add anti-detection or bot-evasion guidance here.
