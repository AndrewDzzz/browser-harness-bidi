# Dialogs

Native alert/confirm/prompt dialogs can freeze page script execution. `page_info()` returns a prompt object when one is pending.

## Detect

```python
info = page_info()
if "prompt" in info:
    print(info["prompt"])
```

## Accept or dismiss

```python
handle_prompt(accept=True)
handle_prompt(accept=False)
```

## Prompt text

```python
handle_prompt(accept=True, text="answer")
```
