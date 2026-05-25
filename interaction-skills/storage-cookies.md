# Storage and cookies

These helpers use page JavaScript for same-origin storage and simple cookie access.

## localStorage

```python
print(get_local_storage())
set_local_storage("key", "value")
clear_local_storage()
```

## sessionStorage

```python
print(get_session_storage())
set_session_storage("step", "1")
clear_session_storage()
```

## Cookies

```python
print(get_cookie_string())
print(get_cookies())
set_cookie("mode", "bidi", same_site="Lax")
clear_cookie("mode")
```

These helpers are intentionally simple. For cross-domain or browser-wide cookie work, prefer a future BiDi storage helper rather than ad hoc script hacks.
