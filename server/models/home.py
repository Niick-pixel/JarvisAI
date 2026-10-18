"""Home Assistant, as Jarvis sees it: whether it is connected, your devices by room, and what a
command did."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HomeConnection(BaseModel):
    url: str
    """Where Home Assistant answers, e.g. http://homeassistant.local:8123."""
    token: str
    """A long-lived access token: Home Assistant > your profile > Security."""


class HomePrefs(BaseModel):
    route_chat: bool
    """Let Home Assistant's own (local) command parser take chat and voice messages it
    recognises, like "turn off the kitchen lights", before they reach the language model."""


class HomeStatus(BaseModel):
    configured: bool
    connected: bool = False
    url: str = ""
    name: str = ""
    """The home's name as set in Home Assistant."""
    version: str = ""
    route_chat: bool = True
    error: str = ""


Action = Literal[
    "on",
    "off",
    "toggle",
    "brightness",
    "temperature",
    "open",
    "close",
    "stop",
    "lock",
    "unlock",
    "play_pause",
    "volume",
    "activate",
    "start",
    "return",
    "press",
]


class Device(BaseModel):
    entity_id: str
    name: str
    domain: str
    area: str
    """The room it is in, or "Other" when Home Assistant has none for it."""
    state: str
    """Home Assistant's raw state: "on", "off", "21.5", "locked", "playing"..."""
    available: bool
    actions: list[Action]
    """What Jarvis can do with it. Empty for sensors, which are shown and never controlled."""
    level: float | None = None
    """0-100: brightness for a light, volume for a speaker, position for blinds."""
    target: float | None = None
    """A thermostat's set point."""
    current: float | None = None
    """A thermostat's or sensor's reading."""
    unit: str = ""
    kind: str = ""
    """Home Assistant's device_class (door, motion, temperature...) - what icon to draw."""
    detail: str = ""
    """One line for the tile, e.g. what a speaker is playing."""


class HomeActionRequest(BaseModel):
    entity_id: str
    action: Action
    value: float | None = None


class AssistRequest(BaseModel):
    text: str
    conversation_id: str | None = None
    """When set, a command Home Assistant handles is written into this chat as a normal turn."""


class AssistResult(BaseModel):
    handled: bool
    """False when Home Assistant did not recognise it as a home command; ask the model instead."""
    reply: str = ""
    conversation_id: str | None = None
