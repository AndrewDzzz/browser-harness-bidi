import browser_harness_bidi.daemon as d


def test_daemon_treats_about_blank_as_real_context():
    assert d._is_real_context({"url": "about:blank", "context": "ctx-1"}) is True
    assert d._is_real_context({"url": "about:blank#ready", "context": "ctx-1"}) is True
    assert d._is_real_context({"url": "about:config", "context": "ctx-1"}) is False
    assert d._is_real_context({"url": "chrome://settings", "context": "ctx-1"}) is False
