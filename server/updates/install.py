"""Handing over to the installer: start it, then close the window so it can replace our files.

The installer is the same JarvisSetup.exe a first install uses, run silently. `/RELAUNCH=1` is
read by packaging/jarvis.iss, which starts Jarvis again once the new files are in place - so an
update looks like a restart that took a few seconds longer.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from server import paths

QUIT_HOOK: list[Callable[[], None]] = []
"""Filled by the desktop launcher with what closes its window. Closing the window is the ordinary
shutdown, which also stops the llama-server we started - whose files the installer replaces."""

INSTALLER_ARGS = ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/RELAUNCH=1"]


def supported() -> bool:
    return paths.frozen() and sys.platform == "win32"


def launch(installer: Path) -> None:
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(  # noqa: S603 - our own verified installer, by absolute path
        [str(installer), *INSTALLER_ARGS], creationflags=flags, close_fds=True
    )
    # Let the HTTP response that asked for this reach the page before the window goes.
    threading.Timer(1.0, _quit).start()


def _quit() -> None:
    if not QUIT_HOOK:
        logging.warning("update: no window to close; the installer will ask Jarvis to close")
    for hook in QUIT_HOOK:
        try:
            hook()
        except Exception:  # noqa: BLE001 - one failing hook must not keep the others from running
            logging.exception("update: closing the window failed")
