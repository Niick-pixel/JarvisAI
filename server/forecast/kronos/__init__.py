"""Kronos, vendored from https://github.com/shiyu-coder/Kronos (MIT, see LICENSE here).

Upstream commit 67b630e67f6a18c9e9be918d9b4337c960db1e9a, `model/kronos.py` and `model/module.py`
copied verbatim except for one line: the absolute `from model.module import *` became a relative
import so the package can live here. Kronos is not on PyPI, which is why it is copied at all.
Keep it verbatim - fixes from upstream should apply with a plain copy - and put anything Jarvis
needs in server/forecast/engine.py instead. Exempt from this repo's lint, types and line limit.
"""

from .kronos import Kronos, KronosTokenizer, auto_regressive_inference

__all__ = ["Kronos", "KronosTokenizer", "auto_regressive_inference"]
