# <site> domain skill

## When to use

Use this skill when working on `<site>` pages that match:

- `<url pattern>`

## Reliable entry points

- Home: `<url>`
- Search: `<url>`
- Settings: `<url>`

## Common page states

- Auth wall: look for `<selector or text>` and stop to ask the user.
- Loaded state: wait for `<selector>`.
- Error state: check `<selector or text>`.

## Useful selectors

```python
wait_for_element("<selector>")
click_selector("<selector>")
get_text("<selector>")
fill_input("<selector>", "value")
```

## Notes

- Keep this durable.
- Do not include credentials or private data.
- Do not include anti-bot or detection-evasion guidance.
