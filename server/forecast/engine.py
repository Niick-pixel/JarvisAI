"""Running Kronos: loading it once, and sampling many futures from a window of bars.

Kronos predicts by sampling, so one run is one possible future. Asking for one averaged path
(what its own `KronosPredictor` does) hides how unsure it is; here every sample is kept, and the
forecast is their median with the band that 80% of them stayed inside.

It runs on the CPU. The GPU belongs to the chat model, and Kronos-small is 25M parameters - a
forecast takes seconds to a minute on a desktop processor, not a card's worth of memory.
PyTorch is imported only here and only when asked, so an install without the forecast extra
starts exactly as before.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from server.forecast.ninjatrader import Bar
from server.forecast.sessions import exchange_time
from server.models.forecast import ForecastStatus
from server.settings import Settings

MAX_CONTEXT = 512
"""Kronos-small and -base were trained on 512 bars; more is truncated."""
CLIP = 5.0
OnStep = Callable[[int, int], None]


@dataclass
class Window:
    bars: list[Bar]
    future: list[int]
    """End times of the bars to predict - real ones in a backtest, the session calendar's live."""


def weights_dir(settings: Settings, repo: str) -> Path:
    return settings.paths.models_dir / "kronos" / repo.split("/")[-1]


def runtime_error() -> str:
    try:
        import torch  # noqa: F401

        from server.forecast import kronos  # noqa: F401
    except ImportError as exc:
        return str(exc)
    return ""


def _stamps(times: list[int]) -> np.ndarray:
    """Kronos's calendar features, in exchange time: minute, hour, weekday, day, month."""
    local = [exchange_time(t) for t in times]
    return np.array([[d.minute, d.hour, d.weekday(), d.day, d.month] for d in local], np.float32)


def _features(bars: list[Bar]) -> np.ndarray:
    """open, high, low, close, volume, amount - amount estimated as Kronos's predictor does."""
    return np.array(
        [[b.o, b.h, b.low, b.c, b.v, b.v * (b.o + b.h + b.low + b.c) / 4] for b in bars], np.float32
    )


class Engine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any = None
        self._tokenizer: Any = None
        self._lock = threading.Lock()

    def _threads(self) -> int:
        # Leave two cores for the window and the chat model's server.
        return self.settings.forecast.threads or max(1, (os.cpu_count() or 4) - 2)

    def status(self) -> ForecastStatus:
        cfg = self.settings.forecast
        model_dir = weights_dir(self.settings, cfg.model)
        files = [
            weights_dir(self.settings, r) / "model.safetensors" for r in (cfg.model, cfg.tokenizer)
        ]
        weights = all(f.is_file() for f in files)
        missing = runtime_error()
        reason, fix = "", ""
        if missing:
            reason = f"PyTorch is not installed ({missing})."
            fix = 'pip install -e ".[forecast]"'
        elif not weights:
            reason = "The Kronos model has not been downloaded yet."
        return ForecastStatus(
            runtime=not missing,
            weights=weights,
            model=cfg.model,
            expected_path=str(model_dir),
            reason=reason,
            fix=fix,
            threads=self._threads(),
        )

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch

        from server.forecast.kronos import Kronos, KronosTokenizer

        cfg = self.settings.forecast
        torch.set_num_threads(self._threads())
        self._tokenizer = KronosTokenizer.from_pretrained(
            str(weights_dir(self.settings, cfg.tokenizer))
        ).eval()
        self._model = Kronos.from_pretrained(str(weights_dir(self.settings, cfg.model))).eval()

    def sample(
        self, windows: list[Window], horizon: int, paths: int, on_step: OnStep
    ) -> np.ndarray:
        """(windows, paths, horizon, 6) in prices - every sampled future of every window."""
        import torch

        from server.forecast.kronos import kronos as upstream

        xs, x_stamps, y_stamps, scale = [], [], [], []
        for window in windows:
            x = _features(window.bars)
            mean, std = x.mean(axis=0), x.std(axis=0)
            xs.append(np.clip((x - mean) / (std + 1e-5), -CLIP, CLIP))
            x_stamps.append(_stamps([b.t for b in window.bars]))
            y_stamps.append(_stamps(window.future))
            scale.append((mean, std))

        def batch(arrays: list[np.ndarray]) -> Any:
            # Each window repeated once per path: one sample each, so none are averaged away.
            return torch.from_numpy(np.repeat(np.stack(arrays), paths, axis=0))

        cfg = self.settings.forecast
        with self._lock:
            self._load()
            # Upstream reports progress through tqdm's trange when verbose; borrow that hook.
            upstream.trange = lambda n: _counting(n, on_step)
            preds = upstream.auto_regressive_inference(
                self._tokenizer,
                self._model,
                batch(xs),
                batch(x_stamps),
                batch(y_stamps),
                MAX_CONTEXT,
                horizon,
                CLIP,
                T=cfg.temperature,
                top_k=0,
                top_p=cfg.top_p,
                sample_count=1,
                verbose=True,
            )
        out = np.asarray(preds)[:, -horizon:, :].reshape(len(windows), paths, horizon, -1)
        for i, (mean, std) in enumerate(scale):
            out[i] = out[i] * (std + 1e-5) + mean
        return out


def _counting(n: int, on_step: OnStep) -> Iterator[int]:
    for i in range(n):
        yield i
        on_step(i + 1, n)


_shared: Engine | None = None


def shared(settings: Settings) -> Engine:
    """One engine per process, so the sheet and an agent's tool share one loaded model."""
    global _shared
    if _shared is None or _shared.settings is not settings:
        _shared = Engine(settings)
    return _shared
