# Selectors

Use selectors when the target is stable, visible, and semantically obvious. Use screenshots and coordinate clicks when the target is primarily visual.

## Wait and read

```python
wait_for_element("main", timeout=10)
print(get_text("main"))
print(get_attr("a", "href"))
```

## Click selector

```python
wait_for_element("button[type='submit']", visible=True)
click_selector("button[type='submit']")
```

`click_selector()` uses `element_rect()` and then a BiDi pointer action through `click_at_xy()`.

## Count and existence

```python
print(count("article"))
if exists(".error"):
    print(get_text(".error"))
```

Avoid writing fragile selectors based on generated classes unless there is no better option.
