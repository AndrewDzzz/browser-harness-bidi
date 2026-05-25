"""Compatibility package for Browser-Harness-BiDi.

The original project exposes `browser_harness`. This fork keeps that import path
but routes the implementation through `bidi_harness`.
"""

from bidi_harness import __version__
