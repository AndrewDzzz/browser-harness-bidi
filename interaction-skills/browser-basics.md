# Browser basics

Reusable bidi mechanics for page state, tabs, screenshots, selectors, and viewport work.

## Screenshots

```python
print(page_info())
path = capture_screenshot()
print(path)
```

Full page:

```python
capture_screenshot("/tmp/full-page.png", full=True)
```

## Tabs and contexts

```python
ctx = new_tab("https://example.com")
wait_for_load()
print(list_tabs())
switch_tab(0)
ensure_real_tab()
close_tab()
```

bidi uses browsing context ids and script realms.

## Selectors

```python
wait_for_element("main", timeout=10)
print(get_text("main"))
print(get_attr("a", "href"))
click_selector("button[type='submit']")
```

Use selectors when the target is stable, visible, and semantically obvious. Use screenshots and coordinate clicks when the target is primarily visual.

## Viewport and PDF

```python
set_viewport(1366, 768)
capture_screenshot("/tmp/viewport.png")
print_pdf("/tmp/page.pdf")
```

`print_pdf()` uses `browsingContext.print`; support can vary by browser and driver version.
