# Connection modes

## Managed Firefox

```bash
bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Show the browser:

```bash
bidi-firefox --headed <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

Use official Firefox privacy-hardening preferences:

```bash
bidi-firefox --privacy-profile <<'PY'
new_tab("https://example.com")
print(js("navigator.webdriver"))
PY
```

`--privacy-profile` is a privacy profile, not an anti-detect profile.

## Managed Chrome

```bash
bidi-chrome <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Show the browser:

```bash
bidi-chrome --headed <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

Use a specific Chrome binary or user data directory:

```bash
bidi-chrome \
  --chrome-binary "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir "$HOME/chrome-bidi-profile" <<'PY'
print(page_info())
PY
```

Attach ChromeDriver to an existing Chrome debug endpoint:

```bash
bidi-chrome --debugger-address 127.0.0.1:9222 <<'PY'
print(list_tabs())
PY
```

## Direct Firefox bidi WebSocket

```bash
firefox --remote-debugging-port 9222
export BIDI_WS=ws://127.0.0.1:9222/session

bidi-harness <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

## WebDriver broker endpoint

Firefox through geckodriver:

```bash
geckodriver --host 127.0.0.1 --port 9516
export BIDI_WEBDRIVER_URL=http://127.0.0.1:9516
export BIDI_BROWSER_NAME=firefox
export BIDI_CAPABILITIES='{"moz:firefoxOptions":{"args":["-headless"]}}'
```

Chrome through ChromeDriver:

```bash
chromedriver --port=9515
export BIDI_WEBDRIVER_URL=http://127.0.0.1:9515
export BIDI_BROWSER_NAME=chrome
```
