# Static documentation sites

Use this for documentation sites with mostly static pages.

## Preferred approach

For simple extraction, prefer HTTP first:

```python
html = http_get(url)
```

Use the browser when JavaScript rendering, screenshots, navigation state, or interactive controls matter.

## Browser flow

```python
new_tab(url)
wait_for_load()
print(page_info())
print(get_text())
```

## Search boxes

If the docs site has a search input:

```python
wait_for_element("input[type='search'], input[placeholder*='Search' i]", timeout=5)
fill_input("input[type='search'], input[placeholder*='Search' i]", query)
press_key("Enter")
```
