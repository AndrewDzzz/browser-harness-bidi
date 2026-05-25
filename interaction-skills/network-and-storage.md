# Network and storage

## Network observation

The daemon subscribes to common WebDriver bidi network events when the browser supports them.

```python
records = network_events()
for record in records:
    print(record["event"], record["method"], record["status"], record["url"])
```

`network_events()` clears the daemon buffer by default. If you need to inspect the same events more than once, save the returned list or call `network_events(clear=False)`.

Summarize by request:

```python
for request in summarize_network(network_events()):
    print(request["method"], request["status"], request["url"])
```

Capture during an action:

```python
capture = capture_network_during(lambda: goto_url("https://example.com"), timeout=10, idle_ms=500)
for request in summarize_network(capture["records"]):
    print(request["method"], request["status"], request["url"])
```

Current limit: this harness observes bidi `network.*` events and groups metadata. Do not claim request interception unless a future helper explicitly implements a bidi-supported interception flow.

## Storage

```python
print(get_local_storage())
set_local_storage("key", "value")
clear_local_storage()

print(get_session_storage())
set_session_storage("step", "1")
clear_session_storage()
```

## Cookies

These helpers use same-origin `document.cookie` and cannot read HttpOnly cookies.

```python
print(get_cookie_string())
print(get_cookies())
set_cookie("mode", "bidi", same_site="Lax")
clear_cookie("mode")
```
