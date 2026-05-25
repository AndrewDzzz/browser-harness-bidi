import json
import time
import traceback


def now_ms():
    return int(time.perf_counter() * 1000)


def clip(text, n=120):
    text = " ".join(str(text or "").split())
    return text[:n]


def wait_until_js(expression, timeout=12.0, interval=0.2):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = js(expression)
            if last:
                return last
        except Exception as exc:
            last = repr(exc)
        time.sleep(interval)
    raise RuntimeError(f"timed out waiting for JS condition: {expression!r}; last={last!r}")


def js_json(expression):
    raw = js(f"JSON.stringify(({expression}))")
    return json.loads(raw) if raw else None


def click_first(selectors, timeout=10.0):
    selector_json = json.dumps(selectors)
    wait_until_js(
        "(()=>{"
        f"for (const s of {selector_json}) {{"
        "  const e = document.querySelector(s);"
        "  if (e) return true;"
        "}"
        "return false;"
        "})()",
        timeout=timeout,
    )
    ok = js(
        "(()=>{"
        f"for (const s of {selector_json}) {{"
        "  const e = document.querySelector(s);"
        "  if (!e) continue;"
        "  e.scrollIntoView({block:'center', inline:'center'});"
        "  e.click();"
        "  return true;"
        "}"
        "return false;"
        "})()"
    )
    if not ok:
        raise RuntimeError(f"no clickable selector found: {selectors}")


def task_1_example():
    new_tab("https://example.com")
    wait_for_load(15)
    wait_until_js("document.querySelector('h1') && document.title")
    return js_json("({title: document.title, h1: document.querySelector('h1').textContent.trim()})")


def task_2_wikipedia():
    new_tab("https://www.wikipedia.org/")
    wait_for_load(20)
    wait_for_element("#searchInput", timeout=15, visible=True)
    fill_input("#searchInput", "WebDriver BiDi")
    press_key("Enter")
    wait_for_load(20)

    is_article = js("location.hostname.includes('wikipedia.org') && location.pathname.startsWith('/wiki/')")
    if not is_article:
        click_first([".mw-search-result-heading a", "li.mw-search-result a", "a[href^='/wiki/']"], timeout=15)
        wait_for_load(20)

    wait_until_js("document.querySelector('h1') && document.querySelector('#mw-content-text')")
    return js_json(
        "(()=>{"
        "const paras = [...document.querySelectorAll('#mw-content-text .mw-parser-output > p')];"
        "const p = paras.map(e => e.textContent.trim()).find(Boolean) || '';"
        "return {title: document.title, url: location.href, paragraph_120: p.slice(0, 120)};"
        "})()"
    )


def task_3_hacker_news():
    new_tab("https://news.ycombinator.com/")
    wait_for_load(20)
    wait_until_js("document.querySelectorAll('.titleline > a').length >= 10", timeout=15)
    return js_json(
        "[...document.querySelectorAll('.titleline > a')].slice(0, 10)"
        ".map(a => ({title: a.textContent.trim(), href: a.href}))"
    )


def task_4_httpbin_form():
    new_tab("https://httpbin.org/forms/post")
    wait_for_load(20)
    wait_for_element("input[name='custname']", timeout=15, visible=True)
    fill_input("input[name='custname']", "bidi speed test")
    fill_input("input[name='custtel']", "123456789")
    fill_input("input[name='custemail']", "test@example.com")
    click_first(["form button[type='submit']", "form input[type='submit']", "form button"], timeout=5)
    wait_for_load(20)
    body = js("document.body ? document.body.innerText : ''")
    return {
        "contains_custname": "bidi speed test" in body,
        "contains_custtel": "123456789" in body,
        "contains_custemail": "test@example.com" in body,
        "url": js("location.href"),
    }


def task_5_mdn():
    new_tab("https://developer.mozilla.org/")
    wait_for_load(25)
    goto_url("https://developer.mozilla.org/en-US/search?q=WebDriver%20BiDi", wait="complete")
    wait_until_js("document.querySelector('main') && document.body.innerText.includes('WebDriver')", timeout=20)
    click_first(
        [
            "main a[href*='WebDriver_BiDi']",
            "main a[href*='WebDriver']",
            "main a[href*='/en-US/docs/']",
        ],
        timeout=15,
    )
    wait_for_load(25)
    wait_until_js("document.querySelector('h1')", timeout=15)
    return js_json("({h1: document.querySelector('h1').textContent.trim(), url: location.href})")


def task_6_python_nav():
    new_tab("https://www.python.org/")
    wait_for_load(20)
    wait_until_js("document.querySelectorAll('nav a, #mainnav a').length >= 5", timeout=15)
    return js_json(
        "[...document.querySelectorAll('nav a, #mainnav a')]"
        ".filter(a => {"
        "  const r = a.getBoundingClientRect();"
        "  const s = getComputedStyle(a);"
        "  return a.textContent.trim() && r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';"
        "})"
        ".map(a => ({text: a.textContent.trim(), href: a.href}))"
    )


def task_7_github_repo():
    new_tab("https://github.com/webdriverio/webdriverio")
    wait_for_load(30)
    wait_until_js("document.querySelector('strong[itemprop=\"name\"] a, h1')", timeout=25)
    return js_json(
        "(()=>{"
        "const text = s => (document.querySelector(s)?.textContent || '').trim().replace(/\\s+/g, ' ');"
        "const repo = text('strong[itemprop=\"name\"] a') || text('h1 strong a') || text('h1');"
        "const stars = text('#repo-stars-counter-star') || text('a[href$=\"/stargazers\"] strong') || text('a[href$=\"/stargazers\"]');"
        "const commitLink = document.querySelector("
        "  '[data-testid=\"latest-commit\"] a[href*=\"/commit/\"], "
        "  ' + 'a[href*=\"/webdriverio/webdriverio/commit/\"][title], "
        "  ' + 'a[href*=\"/commit/\"][title], "
        "  ' + 'a[href*=\"/commit/\"]'"
        ");"
        "const latest_commit_message = (commitLink?.getAttribute('title') || commitLink?.textContent || '').trim().replace(/\\s+/g, ' ');"
        "return {repo, stars, latest_commit_message, url: location.href};"
        "})()"
    )


TASKS = [
    ("task_1_example", task_1_example),
    ("task_2_wikipedia", task_2_wikipedia),
    ("task_3_hacker_news", task_3_hacker_news),
    ("task_4_httpbin_form", task_4_httpbin_form),
    ("task_5_mdn", task_5_mdn),
    ("task_6_python_nav", task_6_python_nav),
    ("task_7_github_repo", task_7_github_repo),
]


results = []
suite_start = now_ms()
for name, fn in TASKS:
    start = now_ms()
    try:
        result = fn()
        results.append({"task": name, "ok": True, "elapsed_ms": now_ms() - start, "result": result})
    except Exception as exc:
        results.append(
            {
                "task": name,
                "ok": False,
                "elapsed_ms": now_ms() - start,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=3),
            }
        )

print("BIDI_SPEED_RESULTS_START")
print(json.dumps({"suite_elapsed_ms": now_ms() - suite_start, "results": results}, ensure_ascii=False, indent=2))
print("BIDI_SPEED_RESULTS_END")
