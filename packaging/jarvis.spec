# PyInstaller spec for the desktop app. Build with:  pyinstaller packaging/jarvis.spec
#
# One *folder*, not one file: a one-file build unpacks several hundred MB (llama.cpp and its CUDA
# runtime) into a temp directory on every launch, which is slow and leaves litter when it crashes.
# The installer wraps this folder, so you still get a single Setup.exe to run.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821 - SPECPATH is injected by PyInstaller
WINDOWS = sys.platform == "win32"

datas = [
    (str(ROOT / "web" / "dist"), "web/dist"),
    (str(ROOT / "server" / "db" / "migrations"), "server/db/migrations"),
    (str(ROOT / "models.toml"), "."),
    (str(ROOT / "config.toml.example"), "."),
]
# The llama.cpp build the CI job downloads lands here; a local build without it simply ships
# without a bundled server, and the app says so rather than failing.
llama = ROOT / "packaging" / "llama"
if llama.is_dir():
    datas.append((str(llama), "llama"))

# sqlite-vec ships its extension as `vec0.so` / `vec0.dll` beside its __init__, and loads it from
# there. PyInstaller's library collector only matches `lib*.so` and friends, so it bundled nothing
# and vector search was silently off in the packaged app - caught by the smoke test, which now
# fails on it. Place the file exactly where the package looks.
import sqlite_vec  # noqa: E402

VEC_DIR = Path(sqlite_vec.__file__).parent
binaries = [(str(f), "sqlite_vec") for f in VEC_DIR.glob("vec0.*") if f.suffix in (".so", ".dll", ".dylib")]

hiddenimports = (
    collect_submodules("server")
    + collect_submodules("uvicorn")
    + collect_submodules("apscheduler")
    + ["webview"]
)

# Voice: the engines ship in the app, the weights do not (Settings > Voice fetches them). Each of
# these carries native libraries or data files beside its code - CTranslate2's DLLs, ONNX Runtime,
# PyAV's FFmpeg, Piper's espeak-ng phoneme data - which only collect_all brings along.
for package in ("faster_whisper", "ctranslate2", "onnxruntime", "av", "tokenizers", "piper"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "torch", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jarvis",
    console=not WINDOWS,  # a windowed app on Windows; a console on Linux keeps the smoke test readable
    icon=str(ROOT / "packaging" / "jarvis.ico") if (ROOT / "packaging" / "jarvis.ico").is_file() else None,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Jarvis", upx=False)  # noqa: F821
