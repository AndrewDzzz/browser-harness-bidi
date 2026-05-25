# Environment variables

This project keeps the public command surface small, but the daemon reads a few environment variables for connection setup, IPC, workspace loading, and compatibility.

## Connection

- `BIDI_WS` - direct WebDriver bidi WebSocket endpoint.
- `WEBDRIVER_BIDI_WS` - compatibility alias for `BIDI_WS`.
- `BIDI_SESSION_READY` - set to `1` when `BIDI_WS` already points at an existing bidi session WebSocket; otherwise the daemon creates a bidi session.
- `BIDI_WEBDRIVER_URL` - WebDriver server root URL. The daemon creates a classic WebDriver session with `webSocketUrl: true` and then connects to the returned bidi WebSocket.
- `WEBDRIVER_URL` - compatibility alias for `BIDI_WEBDRIVER_URL`.
- `BIDI_BROWSER_NAME` - browser name used when creating a WebDriver broker session. Defaults to `chrome`.
- `BIDI_CAPABILITIES` - JSON object merged into the WebDriver capabilities payload.
- `BIDI_HOST` - host used with `BIDI_PORT`. Defaults to `127.0.0.1`.
- `BIDI_PORT` - direct browser bidi port. When set, the daemon builds `ws://BIDI_HOST:BIDI_PORT/session`.
- `BIDI_DELETE_WEBDRIVER_SESSION` - set to `1` to delete the classic WebDriver session on daemon shutdown.

## Daemon and IPC

- `BIDI_NAME` - namespace for daemon sockets, runtime files, and helper connections.
- `BU_NAME` - compatibility alias for `BIDI_NAME`.
- `BIDI_EVENT_BUFFER` - maximum number of browser events kept in the daemon event buffer. Defaults to `500`.
- `BIDI_IPC_TIMEOUT` - helper-to-daemon IPC timeout in seconds. Defaults to `60`.
- `BIDI_RUNTIME_DIR` - directory for daemon runtime socket files.
- `BH_RUNTIME_DIR` - compatibility alias for `BIDI_RUNTIME_DIR`.
- `BIDI_TMP_DIR` - directory for temporary IPC files.
- `BH_TMP_DIR` - compatibility alias for `BIDI_TMP_DIR`.

## Agent workspace

- `BH_AGENT_WORKSPACE` - path to the editable agent workspace. Defaults to `agent-workspace/` in this repository.
- `BH_DOMAIN_SKILLS` - set to `1` to enable domain-skill discovery under `agent-workspace/domain-skills/`.

## Notes

- Prefer `bidi-firefox` for local Firefox automation; it sets the required broker variables for you.
- Prefer `BIDI_WEBDRIVER_URL` over direct port variables when connecting through geckodriver, chromedriver, Selenium Grid, or a cloud provider.
- Do not store credentials, private data, or anti-detection guidance in environment-variable examples.
