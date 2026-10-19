"""Heavy models say so before you download them, with a ballpark speed, and a mixture-of-experts
model is judged by the weights it runs per word, not the ones it stores."""

from server.hardware.heavy import assess
from server.models.hardware import GpuInfo

CARD = GpuInfo(index=0, name="RTX 3080", vram_total_mb=10240, vram_free_mb=9500, vram_used_mb=700)


def judge(mb: int, params: float, active: float | None = None, gpu: GpuInfo | None = CARD):
    return assess(
        display_name="M", weights_mb=mb, params_b=params, active_b=active, gpu=gpu, ram_mb=32768
    )


def test_a_model_that_fits_says_nothing() -> None:
    weight, speed, warning = judge(4900, 8.0)
    assert (weight, warning) == ("light", "") and speed > 30


def test_a_big_dense_model_warns_hard_and_moe_warns_soft() -> None:
    dense = judge(14000, 24.0)
    moe = judge(18000, 30.5, active=3.3)
    assert dense[0] == "heavy" and dense[1] < 8 and dense[2].startswith("Very heavy")
    assert moe[0] == "heavy" and moe[1] > dense[1] and "mixture-of-experts" in moe[2]


def test_too_big_for_card_and_ram_will_not_run() -> None:
    assert judge(42000, 70.0)[0] == "too_heavy"


def test_without_a_gpu_small_models_stay_quiet() -> None:
    assert judge(90, 0.137, gpu=None)[0] == "light"
    weight, _, warning = judge(8900, 14.8, gpu=None)
    assert weight == "heavy" and "processor" in warning
