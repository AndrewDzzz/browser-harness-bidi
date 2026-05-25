import math

import browser_harness_bidi.helpers as h


def test_has_return_statement_detects_top_level_return():
    assert h._has_return_statement("const x = 1; return x") is True


def test_has_return_statement_ignores_inner_arrow_return():
    expression = "JSON.stringify((()=>{const x = 1; return {x}})())"
    assert h._has_return_statement(expression) is False


def test_has_return_statement_ignores_inner_function_return():
    expression = "Array.from([1], function(x) { return x + 1 })"
    assert h._has_return_statement(expression) is False


def test_remote_value_decodes_primitives_and_nested_values():
    value = {
        "type": "object",
        "value": [
            ["name", {"type": "string", "value": "Ada"}],
            ["count", {"type": "number", "value": 3}],
            ["items", {"type": "array", "value": [{"type": "boolean", "value": True}]}],
        ],
    }
    assert h._remote_value(value) == {"name": "Ada", "count": 3, "items": [True]}
    assert math.isnan(h._remote_value({"type": "number", "value": "NaN"}))
    assert h._remote_value({"type": "bigint", "value": "42n"}) == 42


def test_wait_for_element_visible_builds_single_closing_function(monkeypatch):
    seen = []

    def fake_js(expression):
        seen.append(expression)
        return True

    monkeypatch.setattr(h, "js", fake_js)
    assert h.wait_for_element("#ready", visible=True)
    assert seen[0].endswith("})()")
    assert not seen[0].endswith("}})()")


def test_element_rect_parses_json_rect(monkeypatch):
    monkeypatch.setattr(
        h,
        "js",
        lambda expression: '{"x":1,"y":2,"w":3,"h":4,"left":1,"top":2,"right":4,"bottom":6,"cx":2.5,"cy":4}',
    )
    assert h.element_rect("#go") == {
        "x": 1,
        "y": 2,
        "w": 3,
        "h": 4,
        "left": 1,
        "top": 2,
        "right": 4,
        "bottom": 6,
        "cx": 2.5,
        "cy": 4,
    }


def test_click_selector_clicks_center(monkeypatch):
    clicked = {}

    monkeypatch.setattr(h, "element_rect", lambda selector, timeout=0: {"cx": 12, "cy": 34})

    def fake_click(x, y, button="left", clicks=1):
        clicked.update({"x": x, "y": y, "button": button, "clicks": clicks})
        return {"ok": True}

    monkeypatch.setattr(h, "click_at_xy", fake_click)
    assert h.click_selector("#go", button="right", clicks=2) == {"ok": True}
    assert clicked == {"x": 12, "y": 34, "button": "right", "clicks": 2}


def test_storage_helpers_use_js(monkeypatch):
    calls = []

    def fake_js(expression):
        calls.append(expression)
        if "localStorage" in expression and "JSON.stringify" in expression:
            return '{"token":"abc"}'
        if "sessionStorage" in expression and "JSON.stringify" in expression:
            return '{"step":"1"}'
        return None

    monkeypatch.setattr(h, "js", fake_js)
    assert h.get_local_storage() == {"token": "abc"}
    assert h.get_session_storage() == {"step": "1"}
    h.set_local_storage("token", "xyz")
    h.set_session_storage("step", 2)
    h.clear_local_storage()
    h.clear_session_storage()
    assert any("localStorage.setItem" in call for call in calls)
    assert any("sessionStorage.setItem" in call for call in calls)
    assert any("localStorage.clear" in call for call in calls)
    assert any("sessionStorage.clear" in call for call in calls)


def test_cookie_helpers_parse_and_emit_cookie_js(monkeypatch):
    calls = []

    def fake_js(expression):
        calls.append(expression)
        if expression == "document.cookie":
            return "a=1; b=two"
        return None

    monkeypatch.setattr(h, "js", fake_js)
    assert h.get_cookies() == {"a": "1", "b": "two"}
    h.set_cookie("mode", "bidi", same_site="Lax", secure=True)
    h.clear_cookie("mode")
    assert any("SameSite=Lax" in call and "Secure" in call for call in calls)
    assert any("Max-Age=0" in call for call in calls)


def test_domain_skills_for_url_reads_site_directory(tmp_path, monkeypatch):
    workspace = tmp_path / "agent-workspace"
    skill_dir = workspace / "domain-skills" / "github"
    skill_dir.mkdir(parents=True)
    (skill_dir / "repo.md").write_text("# repo\n")
    (skill_dir / "issues.md").write_text("# issues\n")
    monkeypatch.setattr(h, "AGENT_WORKSPACE", workspace)

    assert h.domain_skills_for_url("https://github.com/AndrewDzzz/browser-harness-BiDi") == [
        "issues.md",
        "repo.md",
    ]


def test_goto_url_surfaces_domain_skills_when_enabled(tmp_path, monkeypatch):
    workspace = tmp_path / "agent-workspace"
    skill_dir = workspace / "domain-skills" / "example"
    skill_dir.mkdir(parents=True)
    (skill_dir / "basic.md").write_text("# basic\n")
    monkeypatch.setattr(h, "AGENT_WORKSPACE", workspace)
    monkeypatch.setenv("BH_DOMAIN_SKILLS", "1")
    monkeypatch.setattr(h, "_current_context_id", lambda: "ctx-1")

    calls = []

    def fake_bidi(method, **params):
        calls.append((method, params))
        return {"navigation": "nav-1"}

    monkeypatch.setattr(h, "bidi", fake_bidi)
    result = h.goto_url("https://example.com/demo")

    assert result == {"navigation": "nav-1", "domain_skills": ["basic.md"]}
    assert calls == [
        (
            "browsingContext.navigate",
            {"context": "ctx-1", "url": "https://example.com/demo", "wait": "none"},
        )
    ]


def test_network_events_normalizes_request_and_response(monkeypatch):
    events = [
        {
            "method": "network.beforeRequestSent",
            "params": {
                "context": "ctx-1",
                "request": {
                    "request": "req-1",
                    "url": "https://example.com/api",
                    "method": "GET",
                    "headers": [{"name": "Accept", "value": {"type": "string", "value": "application/json"}}],
                },
            },
        },
        {
            "method": "network.responseCompleted",
            "params": {
                "context": "ctx-1",
                "request": {"request": "req-1", "url": "https://example.com/api"},
                "response": {
                    "url": "https://example.com/api",
                    "status": 200,
                    "statusText": "OK",
                    "headers": [{"name": "Content-Type", "value": {"type": "string", "value": "application/json"}}],
                },
            },
        },
        {"method": "log.entryAdded", "params": {"text": "ignore me"}},
    ]
    monkeypatch.setattr(h, "drain_events", lambda: events)

    records = h.network_events()

    assert records == [
        {
            "event": "network.beforeRequestSent",
            "request_id": "req-1",
            "context": "ctx-1",
            "url": "https://example.com/api",
            "method": "GET",
            "request_headers": {"Accept": "application/json"},
            "status": None,
            "status_text": None,
            "response_headers": {},
            "redirect_count": None,
            "error_text": None,
            "raw": events[0],
        },
        {
            "event": "network.responseCompleted",
            "request_id": "req-1",
            "context": "ctx-1",
            "url": "https://example.com/api",
            "method": None,
            "request_headers": {},
            "status": 200,
            "status_text": "OK",
            "response_headers": {"Content-Type": "application/json"},
            "redirect_count": None,
            "error_text": None,
            "raw": events[1],
        },
    ]


def test_summarize_network_groups_by_request_id():
    records = [
        {
            "event": "network.beforeRequestSent",
            "request_id": "req-1",
            "url": "https://example.com/api",
            "method": "POST",
            "status": None,
            "request_headers": {"Accept": "application/json"},
            "response_headers": {},
            "error_text": None,
        },
        {
            "event": "network.responseCompleted",
            "request_id": "req-1",
            "url": "https://example.com/api",
            "method": None,
            "status": 201,
            "status_text": "Created",
            "request_headers": {},
            "response_headers": {"Content-Type": "application/json"},
            "error_text": None,
        },
    ]

    assert h.summarize_network(records) == [
        {
            "request_id": "req-1",
            "url": "https://example.com/api",
            "method": "POST",
            "status": 201,
            "status_text": "Created",
            "events": ["network.beforeRequestSent", "network.responseCompleted"],
            "error_text": None,
            "request_headers": {"Accept": "application/json"},
            "response_headers": {"Content-Type": "application/json"},
        }
    ]


def test_capture_network_during_runs_action_and_collects(monkeypatch):
    calls = []

    def fake_drain():
        calls.append("drain")
        return []

    monkeypatch.setattr(h, "drain_events", fake_drain)
    monkeypatch.setattr(h, "wait_for_network_idle", lambda timeout, idle_ms: calls.append(("idle", timeout, idle_ms)))
    monkeypatch.setattr(h, "network_events", lambda clear, context, url_contains: [{"url": "https://example.com"}])

    result = h.capture_network_during(lambda: "done", timeout=3, idle_ms=100, url_contains="example", context="ctx")

    assert result == {"result": "done", "records": [{"url": "https://example.com"}]}
    assert calls == ["drain", ("idle", 3, 100)]
