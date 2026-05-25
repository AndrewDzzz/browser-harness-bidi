# Screenshots

Use screenshots to understand visible page state before clicking or typing.

## Basic screenshot

```python
path = capture_screenshot()
print(path)
```

## Full-page screenshot

```python
path = capture_screenshot("/tmp/page.png", full=True)
print(path)
```

## Smaller image for quick inspection

```python
path = capture_screenshot("/tmp/page-small.png", max_dim=1200)
print(path)
```

## Pattern

```python
print(page_info())
path = capture_screenshot()
print(path)
```

After a meaningful visible action, take another screenshot before assuming the action worked.
