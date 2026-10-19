"""The phone companion: pairing, devices, and how to reach Jarvis from the phone."""

from __future__ import annotations

from pydantic import BaseModel


class PairedDevice(BaseModel):
    id: str
    name: str
    created_at: int
    last_seen: int | None = None


class PhoneStatus(BaseModel):
    enabled: bool
    port: int
    addresses: list[str]
    """http://<this PC>:<port> for each network this PC is on - home Wi-Fi, Tailscale."""
    code: str = ""
    """The current one-time pairing code, while pairing is on."""
    code_expires_at: int | None = None
    qr_svg: str = ""
    """A QR code of the pairing link, for the phone's camera."""
    devices: list[PairedDevice] = []
    error: str = ""


class PhoneToggle(BaseModel):
    enabled: bool


class PairRequest(BaseModel):
    code: str
    name: str = "Phone"
