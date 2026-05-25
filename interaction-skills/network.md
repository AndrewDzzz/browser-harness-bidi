# Network

The daemon subscribes to common WebDriver BiDi network events when the browser supports them.

## Drain recent events

```python
for event in drain_events():
    if event["method"].startswith("network."):
        print(event)
```

## Wait for idle

```python
goto_url("https://example.com")
wait_for_load()
wait_for_network_idle(timeout=10, idle_ms=500)
```

BiDi network support is still less exhaustive than Chrome CDP. For deep Chrome-only interception, CDP remains stronger today.
