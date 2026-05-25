# example.com

Use this when testing Browser-Harness-BiDi against `example.com`.

## Flow

```python
new_tab("https://example.com")
wait_for_load()
assert "Example Domain" in get_text()
```

## Useful checks

```python
print(page_info())
print(get_text("h1"))
print(get_attr("a", "href"))
```
