"""From Home Assistant's entities to the devices you recognise, and from a tap to a service call.

Home Assistant reports everything: every sensor attribute, update notices, the sun. The Home
sheet shows the things you would expect in a home app - what you can switch, dim, open, lock,
play or start, plus doors, motion and room temperatures - and leaves the rest to Home Assistant.
"""

from __future__ import annotations

from typing import Any

from server.models.home import Action, Device, HomeActionRequest

ACTIONS: dict[str, list[Action]] = {
    "light": ["toggle", "on", "off", "brightness"],
    "switch": ["toggle", "on", "off"],
    "input_boolean": ["toggle", "on", "off"],
    "fan": ["toggle", "on", "off"],
    "cover": ["open", "close", "stop"],
    "climate": ["temperature", "on", "off"],
    "lock": ["lock", "unlock"],
    "media_player": ["play_pause", "volume", "on", "off"],
    "scene": ["activate"],
    "script": ["activate"],
    "vacuum": ["start", "return"],
    "button": ["press"],
}
SENSOR_KINDS = {
    "sensor": {"temperature", "humidity"},
    "binary_sensor": {"door", "window", "garage_door", "motion", "occupancy", "opening"},
}
OTHER = "Other"


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _level(domain: str, attrs: dict[str, Any]) -> float | None:
    if domain == "light" and attrs.get("brightness") is not None:
        return round(float(attrs["brightness"]) / 255 * 100)
    if domain == "media_player" and attrs.get("volume_level") is not None:
        return round(float(attrs["volume_level"]) * 100)
    if domain == "cover":
        return _number(attrs.get("current_position"))
    if domain == "fan":
        return _number(attrs.get("percentage"))
    return None


def device(entity: dict[str, Any], area: str) -> Device | None:
    entity_id = str(entity.get("entity_id", ""))
    domain = entity_id.split(".", 1)[0]
    attrs: dict[str, Any] = entity.get("attributes") or {}
    kind = str(attrs.get("device_class") or "")
    actions = ACTIONS.get(domain)
    if actions is None and kind not in SENSOR_KINDS.get(domain, set()):
        return None
    state = str(entity.get("state", ""))
    detail = ""
    if domain == "media_player":
        detail = " - ".join(str(attrs[k]) for k in ("media_artist", "media_title") if attrs.get(k))
    elif domain == "climate" and attrs.get("hvac_action"):
        detail = str(attrs["hvac_action"]).replace("_", " ")
    return Device(
        entity_id=entity_id,
        name=str(attrs.get("friendly_name") or entity_id),
        domain=domain,
        area=area or OTHER,
        state=state,
        available=state not in ("unavailable", "unknown"),
        actions=list(actions or []),
        level=_level(domain, attrs),
        target=_number(attrs.get("temperature")) if domain == "climate" else None,
        current=_number(attrs.get("current_temperature") if domain == "climate" else state)
        if domain in ("climate", "sensor")
        else None,
        unit=str(attrs.get("unit_of_measurement") or ""),
        kind=kind,
        detail=detail,
    )


def devices(states: list[dict[str, Any]], areas: dict[str, str]) -> list[Device]:
    found = [device(s, areas.get(str(s.get("entity_id")), "")) for s in states]
    return sorted(
        (d for d in found if d is not None),
        key=lambda d: (d.area == OTHER, d.area.lower(), d.domain in SENSOR_KINDS, d.name.lower()),
    )


def service(request: HomeActionRequest) -> tuple[str, str, dict[str, Any]]:
    """(domain, service, data) for one action. Raises ValueError for one the device lacks."""
    domain = request.entity_id.split(".", 1)[0]
    if request.action not in ACTIONS.get(domain, []):
        raise ValueError(f"{request.entity_id} can't {request.action}.")
    data: dict[str, Any] = {"entity_id": request.entity_id}
    value = request.value
    action = request.action
    if action in ("brightness", "volume", "temperature") and value is None:
        raise ValueError(f"{action} needs a value.")
    simple: dict[str, str] = {
        "on": "turn_on",
        "off": "turn_off",
        "toggle": "toggle",
        "open": "open_cover",
        "close": "close_cover",
        "stop": "stop_cover",
        "lock": "lock",
        "unlock": "unlock",
        "play_pause": "media_play_pause",
        "activate": "turn_on",
        "start": "start",
        "return": "return_to_base",
        "press": "press",
    }
    if action == "brightness":
        return domain, "turn_on", data | {"brightness_pct": max(0, min(100, round(value or 0)))}
    if action == "volume":
        return domain, "volume_set", data | {"volume_level": max(0.0, min(1.0, (value or 0) / 100))}
    if action == "temperature":
        return domain, "set_temperature", data | {"temperature": value}
    return domain, simple[action], data
