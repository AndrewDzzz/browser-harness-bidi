# Tabs and browsing contexts

WebDriver BiDi uses browsing context ids and script realms.

## New tab

```python
ctx = new_tab("https://example.com")
wait_for_load()
print(ctx)
```

## List visible tabs

```python
for i, tab in enumerate(list_tabs()):
    print(i, tab.get("url"), tab.get("context"))
```

## Switch tab

```python
switch_tab(0)
# or
switch_context(context_id)
```

## Ensure usable tab

```python
ensure_real_tab()
print(page_info())
```

## Close current tab

```python
close_tab()
```
