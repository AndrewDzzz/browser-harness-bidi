"""Compatibility package for browser-harness-BiDi.

The original project exposes `browser_harness`. This fork keeps that import path
but routes the implementation through `browser_harness_bidi`.
"""

from browser_harness_bidi import __version__
