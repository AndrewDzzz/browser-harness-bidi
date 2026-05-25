# Network

The daemon subscribes to common WebDriver BiDi network events when the browser supports them.

This skill is observation-only. It captures request/response metadata from BiDi events. It does not intercept, mutate, continue, fulfill, or fail requests.

## Drain recent network events

```python
records = network_events()
for record in records:
    print(record["event"], record["method"], record["status"], record["url"])
```

## Summarize by request

```python
records = network_events()
for request in summarize_network(records):
    print(request["method"], request["status"], request["url"])
```

## Capture during an action

```python
capture = capture_network_during(lambda: goto_url("https://example.com"), timeout=10, idle_ms=500)
print(capture["result"])
for request in summarize_network(capture["records"]):
    print(request["method"], request["status"], request["url"])
```

## Filter URLs

```python
records = network_events(url_contains="/api/")
```

## Wait for idle

```python
goto_url("https://example.com")
wait_for_load()
wait_for_network_idle(timeout=10, idle_ms=500)
```

## Current limits

This harness currently observes BiDi `network.*` events and groups metadata. Do not claim request interception unless a future helper explicitly implements a BiDi-supported interception flow.
