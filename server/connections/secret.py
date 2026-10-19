"""Keeping a password or token on disk without keeping it in the clear.

On Windows the OS encrypts it for this user account (DPAPI, the same thing browsers use for saved
passwords): the file is useless to another account or another PC. Elsewhere the file is written
readable by this user only. Either way it never leaves this machine.
"""

from __future__ import annotations

import base64
import sys

PREFIX_DPAPI = "dpapi:"
PREFIX_PLAIN = "plain:"


def protect(value: str) -> str:
    if sys.platform == "win32":
        return PREFIX_DPAPI + base64.b64encode(_dpapi(value.encode(), encrypt=True)).decode()
    return PREFIX_PLAIN + value


def reveal(stored: str) -> str:
    if stored.startswith(PREFIX_DPAPI):
        if sys.platform != "win32":
            raise ValueError("This credential was saved on Windows and can only be read there.")
        return _dpapi(base64.b64decode(stored[len(PREFIX_DPAPI) :]), encrypt=False).decode()
    return stored.removeprefix(PREFIX_PLAIN)


def _dpapi(data: bytes, *, encrypt: bool) -> bytes:  # pragma: no cover - Windows only
    if sys.platform != "win32":
        raise OSError("DPAPI is Windows only")
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buffer = ctypes.create_string_buffer(data, len(data))
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    out = Blob()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    call = crypt32.CryptProtectData if encrypt else crypt32.CryptUnprotectData
    if not call(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(out)):
        raise OSError("Windows could not protect this credential.")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)
