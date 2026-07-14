"""Browser control helpers built on WebDriver bidi.

Core helpers live here. Agent-editable helpers live in
BH_AGENT_WORKSPACE/agent_helpers.py.
"""

from __future__ import annotations

import base64
import gzip
import importlib.util
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from . import _ipc as ipc

CORE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CORE_DIR.parent.parent
AGENT_WORKSPACE = Path(os.environ.get("BH_AGENT_WORKSPACE", REPO_ROOT / "agent-workspace")).expanduser()
INTERNAL_URL_PREFIXES = ("about:", "chrome:", "chrome-untrusted:", "edge:", "moz-extension:", "chrome-extension:")


def _name() -> str:
    return os.environ.get("BIDI_NAME") or os.environ.get("BU_NAME", "default")


def _is_internal_url(url: str | None) -> bool:
    return (url or "").startswith(INTERNAL_URL_PREFIXES)


def _context_id(context):
    return context.get("context") if isinstance(context, dict) else context


def _load_env_file(path: Path) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _load_env() -> None:
    for path in (REPO_ROOT / ".env", AGENT_WORKSPACE / ".env"):
        if path.exists():
            _load_env_file(path)


_load_env()


def _send(req: dict, timeout: float | None = None) -> dict:
    timeout = timeout or float(os.environ.get("BIDI_IPC_TIMEOUT", "60"))
    c, token = ipc.connect(_name(), timeout=timeout)
    try:
        response = ipc.request(c, token, req)
    finally:
        c.close()
    if "error" in response:
        raise RuntimeError(response["error"])
    return response


def bidi(method: str, params: dict | None = None, **kwargs):
    """Send raw WebDriver bidi.

    Example: bidi("browsingContext.getTree")
    Example: bidi("browsingContext.navigate", context=ctx, url=url, wait="complete")
    """
    payload = dict(params or {})
    payload.update(kwargs)
    return _send({"method": method, "params": payload}).get("result", {})


def drain_events():
    return _send({"meta": "drain_events"})["events"]


def peek_events():
    return _send({"meta": "peek_events"})["events"]


def _current_context_id() -> str:
    ctx = _send({"meta": "current_context"}).get("context")
    if not ctx:
        raise RuntimeError("no active browsing context")
    return ctx


def _flatten_contexts(contexts: list[dict]) -> list[dict]:
    out = []
    for ctx in contexts:
        out.append(ctx)
        out.extend(_flatten_contexts(ctx.get("children") or []))
    return out


def list_contexts(include_children=True, include_internal=True):
    contexts = bidi("browsingContext.getTree").get("contexts", [])
    out = _flatten_contexts(contexts) if include_children else contexts
    if not include_internal:
        out = [ctx for ctx in out if not _is_internal_url(ctx.get("url"))]
    return out


def list_tabs(include_internal=False):
    """Return top-level browsing contexts, newest browser-specific ordering preserved."""
    return [
        ctx
        for ctx in list_contexts(include_children=False, include_internal=include_internal)
        if ctx.get("parent") is None
    ]


def current_context():
    ctx_id = _current_context_id()
    for ctx in list_contexts():
        if ctx.get("context") == ctx_id:
            return ctx
    return {"context": ctx_id}


def switch_context(context):
    ctx_id = _context_id(context)
    try:
        bidi("browsingContext.activate", context=ctx_id)
    except Exception:
        pass
    _send({"meta": "set_context", "context": ctx_id})
    return ctx_id


def new_tab(url="about:blank"):
    result = bidi("browsingContext.create", type="tab")
    ctx = result["context"]
    switch_context(ctx)
    if url != "about:blank":
        nav = goto_url(url)
        if isinstance(nav, dict) and nav.get("domain_skills"):
            return {**nav, "context": ctx}
    return ctx


def switch_tab(tab):
    """Switch to a tab by context id/dict or by zero-based visible-tab index."""
    if isinstance(tab, int):
        tabs = list_tabs()
        try:
            tab = tabs[tab]
        except IndexError as e:
            raise RuntimeError(f"switch_tab: no visible tab at index {tab}; have {len(tabs)}") from e
    return switch_context(tab)


def ensure_real_tab(url="about:blank"):
    """Attach to a non-internal top-level context, creating one if needed."""
    current = None
    try:
        current = current_context()
    except Exception:
        pass
    if current and not _is_internal_url(current.get("url")):
        return current
    tabs = list_tabs(include_internal=False)
    if tabs:
        switch_context(tabs[0])
        return tabs[0]
    ctx = new_tab(url)
    return current_context() if url != "about:blank" else {"context": ctx, "url": url}


def close_context(context=None):
    ctx = _context_id(context)
    ctx = ctx or _current_context_id()
    try:
        current = _current_context_id()
    except Exception:
        current = None
    result = bidi("browsingContext.close", context=ctx)
    if current == ctx:
        _send({"meta": "attach_first_context"})
    return result


def close_tab(tab=None):
    return close_context(tab)


def _domain_skill_dir(url):
    host = urlparse(url).hostname or ""
    host = host.lower().removeprefix("www.")
    slug = []
    previous_dash = False
    for ch in host:
        if ch.isalnum():
            slug.append(ch)
            previous_dash = False
        elif not previous_dash:
            slug.append("-")
            previous_dash = True
    site = "".join(slug).strip("-") or "default"
    return AGENT_WORKSPACE / "domain-skills" / site


def domain_skills_for_url(url, limit=10):
    d = _domain_skill_dir(url)
    if not d.is_dir():
        return []
    return sorted(str(p.relative_to(d)) for p in d.rglob("*.md"))[:limit]


def goto_url(url, wait="none"):
    result = bidi("browsingContext.navigate", context=_current_context_id(), url=url, wait=wait)
    if os.environ.get("BH_DOMAIN_SKILLS") == "1":
        skills = domain_skills_for_url(url)
        if skills:
            result = {**result, "domain_skills": skills}
    return result


def reload(wait="none"):
    return bidi("browsingContext.reload", context=_current_context_id(), wait=wait)


def back(wait="complete"):
    js("history.back()")
    return wait_for_load() if wait else None


def forward(wait="complete"):
    js("history.forward()")
    return wait_for_load() if wait else None


def _js_snippet(expression, limit=160):
    snippet = expression.strip().replace("\n", "\\n")
    return snippet[: limit - 3] + "..." if len(snippet) > limit else snippet


def _has_return_statement(expression):
    """Heuristic for deciding whether to wrap JS in an IIFE.

    We want `const x = 1; return x` to work, but we should not wrap a plain
    expression just because it contains an inner function/arrow return, e.g.
    `JSON.stringify((()=>{ return 1 })())`.
    """
    i = 0
    n = len(expression)
    state = "code"
    quote = ""
    brace_depth = 0
    function_bodies = []
    pending_function_body = False

    def is_ident(ch):
        return ch == "_" or ch == "$" or ch.isalnum()

    def has_token(token):
        before = expression[i - 1] if i > 0 else ""
        after_i = i + len(token)
        after = expression[after_i] if after_i < n else ""
        return expression.startswith(token, i) and not is_ident(before) and not is_ident(after)

    while i < n:
        ch = expression[i]
        nxt = expression[i + 1] if i + 1 < n else ""
        if state == "code":
            if ch in ("'", '"', "`"):
                state = "string"
                quote = ch
                i += 1
                continue
            if ch == "/" and nxt == "/":
                state = "line_comment"
                i += 2
                continue
            if ch == "/" and nxt == "*":
                state = "block_comment"
                i += 2
                continue
            if ch == "=" and nxt == ">":
                pending_function_body = True
                i += 2
                continue
            if has_token("function"):
                pending_function_body = True
                i += len("function")
                continue
            if has_token("return"):
                if not function_bodies:
                    return True
                i += len("return")
                continue
            if ch == "{":
                brace_depth += 1
                if pending_function_body:
                    function_bodies.append(brace_depth)
                    pending_function_body = False
                i += 1
                continue
            if ch == "}":
                if function_bodies and brace_depth == function_bodies[-1]:
                    function_bodies.pop()
                brace_depth = max(0, brace_depth - 1)
                i += 1
                continue
            if ch == ";":
                pending_function_body = False
            i += 1
            continue
        if state == "line_comment":
            if ch == "\n":
                state = "code"
            i += 1
            continue
        if state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue
        if state == "string":
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                state = "code"
                quote = ""
            i += 1
            continue
    return False


def _remote_value(value):
    if not isinstance(value, dict):
        return value
    typ = value.get("type")
    if typ in {"undefined", "null"}:
        return None
    if typ in {"string", "boolean"}:
        return value.get("value")
    if typ == "number":
        raw = value.get("value")
        if raw == "NaN":
            return math.nan
        if raw == "Infinity":
            return math.inf
        if raw == "-Infinity":
            return -math.inf
        return raw
    if typ == "bigint":
        raw = value.get("value")
        return int(raw[:-1]) if isinstance(raw, str) and raw.endswith("n") else raw
    if typ == "array" and isinstance(value.get("value"), list):
        return [_remote_value(item) for item in value["value"]]
    if typ == "object" and isinstance(value.get("value"), list):
        out = {}
        for item in value["value"]:
            if isinstance(item, list) and len(item) == 2:
                key, item_value = item
                if isinstance(key, dict):
                    key = _remote_value(key)
                out[str(key)] = _remote_value(item_value)
        return out if out else value
    return value


def _script_result_value(response, expression):
    if response.get("type") == "exception":
        details = response.get("exceptionDetails") or {}
        text = details.get("text") or details.get("exception", {}).get("description") or "JavaScript evaluation failed"
        raise RuntimeError(f"JavaScript evaluation failed: {text}; expression: {_js_snippet(expression)}")
    if "exceptionDetails" in response:
        details = response.get("exceptionDetails") or {}
        text = details.get("text") or "JavaScript evaluation failed"
        raise RuntimeError(f"JavaScript evaluation failed: {text}; expression: {_js_snippet(expression)}")
    return _remote_value(response.get("result", response))


def js(expression, context=None):
    """Run JavaScript in the active browsing context.

    Expressions with a top-level return are wrapped in an IIFE, so both
    `document.title` and `const x = 1; return x` are valid.
    """
    if _has_return_statement(expression) and not expression.strip().startswith("("):
        expression = f"(function(){{{expression}}})()"
    response = bidi(
        "script.evaluate",
        expression=expression,
        target={"context": context or _current_context_id()},
        awaitPromise=True,
        resultOwnership="none",
    )
    return _script_result_value(response, expression)


def page_info():
    prompt = _send({"meta": "pending_prompt"}).get("prompt")
    if prompt:
        return {"prompt": prompt}
    expression = "JSON.stringify({url:location.href,title:document.title,w:innerWidth,h:innerHeight,sx:scrollX,sy:scrollY,pw:document.documentElement.scrollWidth,ph:document.documentElement.scrollHeight})"
    return json.loads(js(expression))


def wait(seconds=1.0):
    time.sleep(seconds)


def wait_for_load(timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if js("document.readyState") == "complete":
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def wait_for_element(selector, timeout=10.0, visible=False):
    if visible:
        check = (
            f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
            "if(!e)return false;"
            "if(typeof e.checkVisibility==='function')"
            "return e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true});"
            "const s=getComputedStyle(e);"
            "return s.display!=='none'&&s.visibility!=='hidden'&&s.opacity!=='0'})()"
        )
    else:
        check = f"!!document.querySelector({json.dumps(selector)})"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if js(check):
            return True
        time.sleep(0.3)
    return False


def wait_for_text(text, timeout=10.0, selector=None):
    needle = json.dumps(str(text))
    if selector:
        expression = f"((document.querySelector({json.dumps(selector)})||{{innerText:''}}).innerText.includes({needle}))"
    else:
        expression = f"document.body && document.body.innerText.includes({needle})"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if js(expression):
            return True
        time.sleep(0.3)
    return False


def wait_for_network_idle(timeout=10.0, idle_ms=500):
    deadline = time.time() + timeout
    last_activity = time.time()
    inflight = set()
    active_context = _current_context_id()
    while time.time() < deadline:
        for event in drain_events():
            method = event.get("method") or ""
            params = event.get("params") or {}
            event_context = params.get("context") or (params.get("request") or {}).get("context")
            if event_context and event_context != active_context:
                continue
            request = params.get("request") or {}
            request_id = request.get("request") or request.get("id") or params.get("request")
            if method == "network.beforeRequestSent":
                inflight.add(request_id)
                last_activity = time.time()
            elif method in {"network.responseCompleted", "network.fetchError"}:
                inflight.discard(request_id)
                last_activity = time.time()
            elif method.startswith("network."):
                last_activity = time.time()
        if not inflight and (time.time() - last_activity) * 1000 >= idle_ms:
            return True
        time.sleep(0.1)
    return False


def _network_event_context(params):
    request = params.get("request") if isinstance(params.get("request"), dict) else {}
    return params.get("context") or request.get("context")


def _network_event_request_id(params):
    request = params.get("request") if isinstance(params.get("request"), dict) else {}
    raw = request.get("request") or request.get("id") or params.get("request")
    return raw if isinstance(raw, str) else None


def _network_event_url(params):
    request = params.get("request") if isinstance(params.get("request"), dict) else {}
    response = params.get("response") if isinstance(params.get("response"), dict) else {}
    return request.get("url") or response.get("url")


def _network_event_method(params):
    request = params.get("request") if isinstance(params.get("request"), dict) else {}
    return request.get("method")


def _network_event_headers(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    out = {}
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            raw_value = item.get("value")
            if isinstance(raw_value, dict):
                raw_value = raw_value.get("value")
            if name is not None:
                out[str(name)] = raw_value
    return out


def _network_capture_record(event):
    method = event.get("method") or ""
    params = event.get("params") or {}
    request = params.get("request") if isinstance(params.get("request"), dict) else {}
    response = params.get("response") if isinstance(params.get("response"), dict) else {}
    return {
        "event": method,
        "request_id": _network_event_request_id(params),
        "context": _network_event_context(params),
        "url": _network_event_url(params),
        "method": _network_event_method(params),
        "request_headers": _network_event_headers(request.get("headers")),
        "status": response.get("status"),
        "status_text": response.get("statusText"),
        "response_headers": _network_event_headers(response.get("headers")),
        "redirect_count": params.get("redirectCount"),
        "error_text": params.get("errorText"),
        "raw": event,
    }


def network_events(clear=True, context=None, url_contains=None, event_prefix="network."):
    """Return buffered bidi network events as normalized records.

    This is observation-only. It does not intercept, mutate, continue, fulfill,
    or fail requests.
    """
    events = drain_events() if clear else peek_events()
    ctx = _context_id(context) if context is not None else None
    out = []
    for event in events:
        method = event.get("method") or ""
        if event_prefix and not method.startswith(event_prefix):
            continue
        record = _network_capture_record(event)
        if ctx and record.get("context") != ctx:
            continue
        if url_contains and url_contains not in (record.get("url") or ""):
            continue
        out.append(record)
    return out


def capture_network_during(action, timeout=10.0, idle_ms=500, url_contains=None, context=None):
    """Run `action()` and return observed request/response records.

    Example:
        records = capture_network_during(lambda: goto_url("https://example.com"))
    """
    drain_events()
    result = action()
    wait_for_network_idle(timeout=timeout, idle_ms=idle_ms)
    records = network_events(clear=True, context=context, url_contains=url_contains)
    return {"result": result, "records": records}


def summarize_network(records):
    """Group normalized network records by request id."""
    grouped = {}
    for record in records:
        request_id = record.get("request_id") or f"{record.get('event')}:{record.get('url')}"
        item = grouped.setdefault(
            request_id,
            {
                "request_id": record.get("request_id"),
                "url": record.get("url"),
                "method": record.get("method"),
                "status": None,
                "events": [],
                "error_text": None,
                "request_headers": {},
                "response_headers": {},
            },
        )
        item["events"].append(record.get("event"))
        if record.get("url"):
            item["url"] = record.get("url")
        if record.get("method"):
            item["method"] = record.get("method")
        if record.get("status") is not None:
            item["status"] = record.get("status")
            item["status_text"] = record.get("status_text")
        if record.get("error_text"):
            item["error_text"] = record.get("error_text")
        if record.get("request_headers"):
            item["request_headers"].update(record.get("request_headers") or {})
        if record.get("response_headers"):
            item["response_headers"].update(record.get("response_headers") or {})
    return list(grouped.values())


_BUTTONS = {"left": 0, "middle": 1, "right": 2}
_SPECIAL_KEYS = {
    "Backspace": "\ue003",
    "Tab": "\ue004",
    "Enter": "\ue007",
    "Shift": "\ue008",
    "Control": "\ue009",
    "Alt": "\ue00a",
    "Escape": "\ue00c",
    " ": "\ue00d",
    "PageUp": "\ue00e",
    "PageDown": "\ue00f",
    "End": "\ue010",
    "Home": "\ue011",
    "ArrowLeft": "\ue012",
    "ArrowUp": "\ue013",
    "ArrowRight": "\ue014",
    "ArrowDown": "\ue015",
    "Delete": "\ue017",
    "Meta": "\ue03d",
}
_MODIFIERS = [(1, "Alt"), (2, "Control"), (4, "Meta"), (8, "Shift")]


def _key_value(key):
    return _SPECIAL_KEYS.get(key, key)


def _perform_actions(actions):
    result = bidi("input.performActions", context=_current_context_id(), actions=actions)
    try:
        bidi("input.releaseActions", context=_current_context_id())
    except Exception:
        pass
    return result


def click_at_xy(x, y, button="left", clicks=1):
    btn = _BUTTONS.get(button, button if isinstance(button, int) else 0)
    pointer_actions = [{"type": "pointerMove", "x": int(x), "y": int(y), "origin": "viewport"}]
    for _ in range(clicks):
        pointer_actions.append({"type": "pointerDown", "button": btn})
        pointer_actions.append({"type": "pointerUp", "button": btn})
    return _perform_actions(
        [
            {
                "type": "pointer",
                "id": "mouse",
                "parameters": {"pointerType": "mouse"},
                "actions": pointer_actions,
            }
        ]
    )


def scroll(x, y, dy=-300, dx=0):
    return _perform_actions(
        [
            {
                "type": "wheel",
                "id": "wheel",
                "actions": [
                    {"type": "scroll", "x": int(x), "y": int(y), "deltaX": int(dx), "deltaY": int(dy), "origin": "viewport"}
                ],
            }
        ]
    )


def press_key(key, modifiers=0):
    actions = []
    for bit, modifier in _MODIFIERS:
        if modifiers & bit:
            actions.append({"type": "keyDown", "value": _key_value(modifier)})
    actions.append({"type": "keyDown", "value": _key_value(key)})
    actions.append({"type": "keyUp", "value": _key_value(key)})
    for bit, modifier in reversed(_MODIFIERS):
        if modifiers & bit:
            actions.append({"type": "keyUp", "value": _key_value(modifier)})
    return _perform_actions([{"type": "key", "id": "keyboard", "actions": actions}])


def type_text(text):
    actions = []
    for ch in str(text):
        value = _key_value("Enter") if ch == "\n" else ch
        actions.append({"type": "keyDown", "value": value})
        actions.append({"type": "keyUp", "value": value})
    return _perform_actions([{"type": "key", "id": "keyboard", "actions": actions}])


def fill_input(selector, text, clear_first=True, timeout=0.0):
    if timeout > 0 and not wait_for_element(selector, timeout=timeout):
        raise RuntimeError(f"fill_input: element not found: {selector!r}")
    focused = js(
        f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
        "if(!e)return false;e.focus();return true;})()"
    )
    if not focused:
        raise RuntimeError(f"fill_input: element not found: {selector!r}")
    if clear_first:
        press_key("a", modifiers=4 if sys.platform == "darwin" else 2)
        press_key("Backspace")
    type_text(text)
    js(
        f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
        "if(!e)return;"
        "e.dispatchEvent(new Event('input',{bubbles:true}));"
        "e.dispatchEvent(new Event('change',{bubbles:true}));}})()"
    )


def element_rect(selector, timeout=0.0):
    if timeout > 0 and not wait_for_element(selector, timeout=timeout):
        raise RuntimeError(f"element_rect: element not found: {selector!r}")
    result = js(
        f"(JSON.stringify((()=>{{const e=document.querySelector({json.dumps(selector)});"
        "if(!e)return null;"
        "const r=e.getBoundingClientRect();"
        "return {x:r.x,y:r.y,w:r.width,h:r.height,left:r.left,top:r.top,right:r.right,bottom:r.bottom,"
        "cx:r.x+r.width/2,cy:r.y+r.height/2};})()))"
    )
    rect = json.loads(result) if result else None
    if rect is None:
        raise RuntimeError(f"element_rect: element not found: {selector!r}")
    return rect


def click_selector(selector, timeout=10.0, button="left", clicks=1):
    rect = element_rect(selector, timeout=timeout)
    return click_at_xy(rect["cx"], rect["cy"], button=button, clicks=clicks)


def scroll_to_element(selector, block="center", inline="center", timeout=10.0):
    if timeout > 0 and not wait_for_element(selector, timeout=timeout):
        raise RuntimeError(f"scroll_to_element: element not found: {selector!r}")
    ok = js(
        f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
        "if(!e)return false;"
        f"e.scrollIntoView({{block:{json.dumps(block)},inline:{json.dumps(inline)}}});"
        "return true;})()"
    )
    if not ok:
        raise RuntimeError(f"scroll_to_element: element not found: {selector!r}")
    return element_rect(selector)


def get_text(selector=None):
    if selector is None:
        return js("document.body ? document.body.innerText : ''")
    return js(f"((document.querySelector({json.dumps(selector)})||{{innerText:null}}).innerText)")


def get_html(selector=None):
    if selector is None:
        return js("document.documentElement.outerHTML")
    return js(f"((document.querySelector({json.dumps(selector)})||{{innerHTML:null}}).innerHTML)")


def get_value(selector):
    return js(f"((document.querySelector({json.dumps(selector)})||{{value:null}}).value)")


def get_attr(selector, name):
    return js(
        f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
        f"return e?e.getAttribute({json.dumps(name)}):null;}})()"
    )


def count(selector):
    return js(f"document.querySelectorAll({json.dumps(selector)}).length")


def exists(selector):
    return bool(js(f"!!document.querySelector({json.dumps(selector)})"))


def capture_screenshot(path=None, full=False, max_dim=None):
    path = path or str(ipc._TMP / "bidi-shot.png")
    result = bidi(
        "browsingContext.captureScreenshot",
        context=_current_context_id(),
        origin="document" if full else "viewport",
    )
    data = result["data"]
    Path(path).write_bytes(base64.b64decode(data))
    if max_dim:
        from PIL import Image

        img = Image.open(path)
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim))
            img.save(path)
    return path


def print_pdf(path=None, **options):
    """Print the current browsing context to PDF using WebDriver bidi."""
    path = path or str(ipc._TMP / "bidi-page.pdf")
    result = bidi("browsingContext.print", context=_current_context_id(), **options)
    data = result.get("data")
    if not data:
        raise RuntimeError(f"print_pdf: browsingContext.print returned no data: {result}")
    Path(path).write_bytes(base64.b64decode(data))
    return path


def upload_file(selector, path):
    files = [path] if isinstance(path, str) else list(path)
    files = [str(Path(p).expanduser().resolve()) for p in files]
    expression = f"document.querySelector({json.dumps(selector)})"
    response = bidi(
        "script.evaluate",
        expression=expression,
        target={"context": _current_context_id()},
        awaitPromise=True,
        resultOwnership="root",
    )
    node = response.get("result") or {}
    shared_id = node.get("sharedId") or node.get("handle")
    if not shared_id:
        raise RuntimeError(f"upload_file: no element sharedId for selector {selector!r}")
    return bidi("input.setFiles", context=_current_context_id(), element={"sharedId": shared_id}, files=files)


def handle_prompt(accept=True, text=None):
    prompt = _send({"meta": "pending_prompt"}).get("prompt")
    params = {"context": _current_context_id(), "accept": bool(accept)}
    if text is not None:
        params["userText"] = str(text)
    result = bidi("browsingContext.handleUserPrompt", **params)
    return {"prompt": prompt, "result": result}


def set_viewport(width, height, device_pixel_ratio=None):
    params = {"context": _current_context_id(), "viewport": {"width": int(width), "height": int(height)}}
    if device_pixel_ratio is not None:
        params["devicePixelRatio"] = float(device_pixel_ratio)
    return bidi("browsingContext.setViewport", **params)


def get_local_storage():
    return json.loads(js("JSON.stringify(Object.assign({}, localStorage))"))


def set_local_storage(key, value):
    js(f"localStorage.setItem({json.dumps(str(key))}, {json.dumps(str(value))})")


def clear_local_storage():
    js("localStorage.clear()")


def get_session_storage():
    return json.loads(js("JSON.stringify(Object.assign({}, sessionStorage))"))


def set_session_storage(key, value):
    js(f"sessionStorage.setItem({json.dumps(str(key))}, {json.dumps(str(value))})")


def clear_session_storage():
    js("sessionStorage.clear()")


def get_cookie_string():
    return js("document.cookie")


def get_cookies():
    raw = get_cookie_string()
    if not raw:
        return {}
    out = {}
    for item in raw.split("; "):
        if "=" in item:
            key, value = item.split("=", 1)
            out[key] = value
    return out


def set_cookie(name, value, path="/", max_age=None, same_site=None, secure=False):
    parts = [f"{name}={value}", f"Path={path}"]
    if max_age is not None:
        parts.append(f"Max-Age={int(max_age)}")
    if same_site:
        parts.append(f"SameSite={same_site}")
    if secure:
        parts.append("Secure")
    js(f"document.cookie = {json.dumps('; '.join(parts))}")


def clear_cookie(name, path="/"):
    set_cookie(name, "", path=path, max_age=0)


def http_get(url, headers=None, timeout=20.0):
    request_headers = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
    if headers:
        request_headers.update(headers)
    with urllib.request.urlopen(urllib.request.Request(url, headers=request_headers), timeout=timeout) as response:
        data = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data.decode()


def _load_agent_helpers():
    path = AGENT_WORKSPACE / "agent_helpers.py"
    if not path.exists():
        return
    spec = importlib.util.spec_from_file_location("browser_harness_bidi_agent_helpers", path)
    if not spec or not spec.loader:
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, value in vars(module).items():
        if not name.startswith("_"):
            globals()[name] = value


_load_agent_helpers()
