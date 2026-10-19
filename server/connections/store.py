"""The saved accounts, in `data/connections.json` - entered in Settings, never in a config file.

Each credential is stored through `secret.protect`; everything else (an address, a login name) is
plain so the Settings page can show it without decrypting anything.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any

from server.connections import secret


class Accounts:
    def __init__(self, data_dir: Path) -> None:
        self._file = data_dir / "connections.json"
        try:
            self._saved: dict[str, dict[str, Any]] = json.loads(self._file.read_text())
        except (OSError, ValueError):
            self._saved = {}

    def get(self, name: str) -> dict[str, Any] | None:
        return self._saved.get(name)

    def credential(self, name: str) -> str:
        entry = self._saved.get(name) or {}
        return secret.reveal(str(entry.get("secret", ""))) if entry.get("secret") else ""

    def save(self, name: str, credential: str, **public: Any) -> None:
        self._saved[name] = {**public, "secret": secret.protect(credential)}
        self._write()

    def remove(self, name: str) -> None:
        self._saved.pop(name, None)
        self._write()

    def _write(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(self._saved, indent=1))
        with contextlib.suppress(OSError):
            os.chmod(self._file, 0o600)
