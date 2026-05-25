# Forms and input

Use user-like bidi actions first. Use DOM reads when selectors are stable.

## Fill and submit

```python
fill_input("input[name='name']", "bidi user", timeout=10)
fill_input("textarea[name='comment']", "Submitted by browser-harness-bidi")
click_selector("button[type='submit']")
wait_for_load(timeout=10)
```

Keyboard submit:

```python
fill_input("input[type='search']", "webdriver bidi")
press_key("Enter")
wait_for_network_idle(timeout=10)
```

After any submit action, wait for the page's real completion signal: navigation load, network idle, or a stable result selector.

Read values:

```python
print(get_value("input[name='email']"))
```

If the page asks for credentials, stop and ask the user. Do not infer, invent, or type secrets from screenshots.

## Uploads

```python
upload_file("input[type='file']", "/absolute/path/file.pdf")
upload_file("input[type='file']", ["/absolute/path/a.png", "/absolute/path/b.png"])
```

If the file input is hidden behind a button, use the visible button first to open the upload state, then call `upload_file()` on the actual input.

## Dialogs

```python
info = page_info()
if "prompt" in info:
    print(info["prompt"])

handle_prompt(accept=True)
handle_prompt(accept=False)
handle_prompt(accept=True, text="answer")
```
