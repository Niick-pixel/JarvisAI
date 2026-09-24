"""Put llama.cpp's official Windows CUDA build into packaging/llama/, for the bundle.

Asset names change between releases, so this asks the release which assets it has instead of
hardcoding one. It prefers CUDA 12 over 13: 13 needs a newer driver than a lot of cards run, and a
bundle that refuses to start on your driver is worse than one a few percent slower.

    python packaging/fetch_llama.py b11139
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "ggml-org/llama.cpp"
TARGET = Path(__file__).resolve().parent / "llama"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=300) as response:
        return bytes(response.read())


def pick(assets: list[dict[str, str]], prefix: str) -> dict[str, str]:
    pattern = re.compile(rf"^{prefix}-bin-win-cuda-(\d+)\.(\d+)-x64\.zip$")
    found = [(m, a) for a in assets if (m := pattern.match(a["name"]))]
    twelve = [(m, a) for m, a in found if m.group(1) == "12"]
    pool = twelve or found
    if not pool:
        names = ", ".join(a["name"] for a in assets)
        raise SystemExit(f"no Windows CUDA asset matching {prefix}-bin-win-cuda-*; have: {names}")
    return max(pool, key=lambda item: (int(item[0].group(1)), int(item[0].group(2))))[1]


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "b11139"
    release = json.loads(_get(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}"))
    assets = release["assets"]
    chosen = [pick(assets, f"llama-{tag}"), pick(assets, "cudart-llama")]
    TARGET.mkdir(parents=True, exist_ok=True)
    for asset in chosen:
        print(f"fetching {asset['name']}")
        with zipfile.ZipFile(io.BytesIO(_get(asset["browser_download_url"]))) as archive:
            archive.extractall(TARGET)
    # Some releases nest everything in a folder; the app looks for llama/llama-server.exe.
    server = next(TARGET.rglob("llama-server.exe"), None)
    if server is None:
        raise SystemExit("the release did not contain llama-server.exe")
    if server.parent != TARGET:
        for item in server.parent.iterdir():
            item.replace(TARGET / item.name)
    (TARGET / "SOURCE.txt").write_text(
        f"llama.cpp {tag} (MIT), from https://github.com/{REPO}/releases/tag/{tag}\n"
        + "".join(f"  {a['name']}\n" for a in chosen)
    )
    print(f"llama-server.exe and its CUDA runtime are in {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
