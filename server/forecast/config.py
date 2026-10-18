"""[forecast] in config.toml. Its own module because settings.py is at its length limit."""

from __future__ import annotations

from pydantic import BaseModel


class ForecastConfig(BaseModel):
    model: str = "NeoQuasar/Kronos-small"
    """25M parameters, 512 bars of context. Kronos-base (102M) is slower and not clearly better on
    five-minute futures; check with the backtest before switching."""
    tokenizer: str = "NeoQuasar/Kronos-Tokenizer-base"
    lookback: int = 400
    """Bars the model sees: about 33 hours of five-minute bars. Capped at 512 by the model."""
    paths: int = 16
    """Sampled futures per forecast. More gives a steadier band and takes proportionally longer."""
    backtest_paths: int = 6
    temperature: float = 1.0
    top_p: float = 0.9
    threads: int = 0
    """CPU threads for PyTorch. 0 means all but two."""
