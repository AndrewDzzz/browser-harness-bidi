# Domain skills

Domain skills are optional, site-specific playbooks that agents can read before inventing a new browser flow.

They are disabled by default. Enable them with:

```bash
export BH_DOMAIN_SKILLS=1
```

When enabled, `goto_url(url)` returns up to 10 Markdown filenames found under:

```text
agent-workspace/domain-skills/<site>/
```

The `<site>` directory is derived from the hostname by removing `www.` and taking the first domain label. For example:

```text
https://github.com/browser-use/browser-harness -> agent-workspace/domain-skills/github/
https://docs.python.org/3/ -> agent-workspace/domain-skills/docs/
```

## What belongs here

Good domain skills capture durable site knowledge:

- stable URL patterns
- reliable selectors
- common page states
- login/auth-wall clues
- hidden waits
- export/download flows
- known iframe or shadow DOM traps

Avoid storing:

- credentials, cookies, tokens, or private data
- one-off task notes
- fragile pixel coordinates
- instructions for bypassing site security, bot detection, or rate limits

## BiDi style

Prefer browser-harness-BiDi helpers:

```python
new_tab(url)
wait_for_load()
wait_for_element(selector)
click_selector(selector)
fill_input(selector, text)
get_text(selector)
js(expression)
bidi("module.command", ...)
```

Use screenshots and coordinate clicks for visual work, but keep domain skills selector/flow-oriented so they survive layout changes.
