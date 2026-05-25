# Forms

Use `fill_input()` for framework-managed inputs because it focuses, types, and dispatches input/change events.

## Fill and submit

```python
fill_input("input[name='email']", "user@example.com", timeout=10)
fill_input("input[name='password']", "not-from-screenshot")
click_selector("button[type='submit']")
```

## Keyboard submit

```python
fill_input("input[type='search']", "webdriver bidi")
press_key("Enter")
```

## Values

```python
print(get_value("input[name='email']"))
```

If the page asks for credentials, stop and ask the user. Do not infer or type secrets from screenshots.
