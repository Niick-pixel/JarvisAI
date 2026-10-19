"""The image and video models offered for download. Turbo models: a picture in a few steps.

Like models.toml, files are resolved against Hugging Face when you press download - the real name,
size and sha256 - so an entry that no longer resolves shows as unavailable instead of failing.

The small SD models are one file. The newer ones come in parts - the diffusion model, a VAE that
turns its output into pixels, and one or two text encoders that read your prompt - each passed to
stable-diffusion.cpp under its own flag (server/imagegen/parts.py). A part shared by two models
(FLUX's VAE serves Z-Image too) has one `save_as` name and is downloaded once.
"""

from __future__ import annotations

from typing import Any

FLUX_VAE = {
    "hf_repo": "black-forest-labs/FLUX.1-schnell",
    "file_glob": "ae.safetensors",
    "save_as": "flux-ae.safetensors",
}

IMAGE_MODELS: list[dict[str, Any]] = [
    {
        "key": "sd-turbo",
        "display_name": "SD Turbo",
        "hf_repo": "stabilityai/sd-turbo",
        "file_glob": "sd_turbo.safetensors",
        "width": 512,
        "height": 512,
        "steps": 4,
        "cfg": 1.0,
        "why": "Fast: a 512 px picture in a few seconds on a mid-range GPU. Smallest to download.",
        "license": "Stability AI Community License",
    },
    {
        "key": "sdxl-turbo",
        "display_name": "SDXL Turbo",
        "hf_repo": "stabilityai/sdxl-turbo",
        "file_glob": "sd_xl_turbo_1.0_fp16.safetensors",
        "width": 512,
        "height": 512,
        "steps": 4,
        "cfg": 1.0,
        "why": "Noticeably better pictures than SD Turbo, for about twice the time and VRAM.",
        "license": "Stability AI Community License",
    },
    {
        "key": "z-image-turbo",
        "display_name": "Z-Image Turbo",
        "parts": {
            "diffusion_model": {
                "hf_repo": "leejet/Z-Image-Turbo-GGUF",
                "file_glob": "*Q4_K*.gguf",
                "save_as": "z_image_turbo-q4_k.gguf",
            },
            "llm": {
                "hf_repo": "unsloth/Qwen3-4B-Instruct-2507-GGUF",
                "file_glob": "*Q4_K_M.gguf",
                "save_as": "qwen3-4b-instruct-2507-q4_k_m.gguf",
            },
            "vae": FLUX_VAE,
        },
        "width": 1024,
        "height": 1024,
        "steps": 8,
        "cfg": 1.0,
        "sampler": "euler",
        "args": ["--offload-to-cpu"],
        "size_gb": 6.2,
        "why": "The best pictures that fit a 10 GB card: real detail, and it can write text in an "
        "image. About 6 GB to download; around half a minute a picture.",
        "license": "Apache 2.0",
    },
    {
        "key": "flux-schnell",
        "display_name": "FLUX.1 schnell",
        "heavy": True,
        "parts": {
            "diffusion_model": {
                "hf_repo": "leejet/FLUX.1-schnell-gguf",
                "file_glob": "*q4_0.gguf",
                "save_as": "flux1-schnell-q4_0.gguf",
            },
            "clip_l": {
                "hf_repo": "comfyanonymous/flux_text_encoders",
                "file_glob": "clip_l.safetensors",
                "save_as": "clip_l.safetensors",
            },
            "t5xxl": {
                "hf_repo": "city96/t5-v1_1-xxl-encoder-gguf",
                "file_glob": "*Q4_K_M.gguf",
                "save_as": "t5xxl-q4_k_m.gguf",
            },
            "vae": FLUX_VAE,
        },
        "width": 1024,
        "height": 1024,
        "steps": 4,
        "cfg": 1.0,
        "sampler": "euler",
        "args": ["--clip-on-cpu", "--offload-to-cpu"],
        "size_gb": 10.2,
        "why": "Heavy: about 10 GB to download and the GPU fully busy for most of a minute per "
        "picture. Excellent prompt following.",
        "license": "Apache 2.0",
    },
    {
        "key": "wan2.1-t2v-1.3b",
        "display_name": "Wan 2.1 video (1.3B)",
        "video": True,
        "heavy": True,
        "parts": {
            "diffusion_model": {
                "hf_repo": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
                "file_glob": "split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors",
                "save_as": "wan2.1_t2v_1.3B_fp16.safetensors",
            },
            "vae": {
                "hf_repo": "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
                "file_glob": "split_files/vae/wan_2.1_vae.safetensors",
                "save_as": "wan_2.1_vae.safetensors",
            },
            "t5xxl": {
                "hf_repo": "city96/umt5-xxl-encoder-gguf",
                "file_glob": "*Q4_K_M.gguf",
                "save_as": "umt5-xxl-encoder-q4_k_m.gguf",
            },
        },
        "width": 832,
        "height": 480,
        "steps": 20,
        "cfg": 6.0,
        "sampler": "euler",
        "frames": 33,
        "args": ["--flow-shift", "3.0", "--offload-to-cpu"],
        "negative": "blurry, static, still image, low quality, distorted, deformed, extra limbs, "
        "watermark, subtitles",
        "size_gb": 6.8,
        "why": "Experimental: a two-second clip (832x480) from a description. Expect several "
        "minutes per clip with the GPU fully busy; about 7 GB to download.",
        "license": "Apache 2.0",
    },
]


def video_key() -> str | None:
    """The video model - there is one, and it is chosen apart from the picture model."""
    return next((m["key"] for m in IMAGE_MODELS if m.get("video")), None)


def entry(key: str) -> dict[str, Any] | None:
    return next((m for m in IMAGE_MODELS if m["key"] == key), None)
