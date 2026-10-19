"""Reading a schedule out of plain words: "every weekday at 7am" -> `0 7 * * 1-5`.

Deliberately not a model's job. A schedule is the one part of a workflow that must be exactly
right, and a dozen readable rules get it right every time - or say plainly that they could not, so
the form asks you instead of guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DAY_NAMES = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}
PARTS_OF_DAY = {
    "morning": (8, 0),
    "noon": (12, 0),
    "midday": (12, 0),
    "lunchtime": (12, 0),
    "afternoon": (15, 0),
    "evening": (18, 0),
    "night": (21, 0),
    "tonight": (21, 0),
    "midnight": (0, 0),
}

AT_TIME = re.compile(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", re.I)
BARE_TIME = re.compile(r"\b(\d{1,2})(?::(\d{2}))\s*(am|pm)?\b|\b(\d{1,2})\s*(am|pm)\b", re.I)
EVERY_MINUTES = re.compile(r"\bevery\s+(\d{1,2})\s*(?:minutes|mins?)\b", re.I)
EVERY_HOURS = re.compile(r"\bevery\s+(\d{1,2})\s*hours?\b", re.I)
HOURLY = re.compile(r"\b(hourly|every hour|each hour)\b", re.I)
WEEKDAYS = re.compile(
    r"\b(weekdays?|every weekday|work ?days?|monday (?:to|through|-) friday)\b", re.I
)
WEEKENDS = re.compile(r"\b(weekends?)\b", re.I)
DAILY = re.compile(
    r"\b(daily|every day|each day|every (?:morning|evening|night|afternoon))\b", re.I
)


@dataclass
class Schedule:
    cron: str

    @property
    def said(self) -> str:
        """Read back in words, so the draft shows what was understood - not what was typed."""
        return describe(self.cron)


def describe(cron: str) -> str:
    minute, hour, _, _, dow = cron.split()
    if minute.startswith("*/"):
        return f"Every {minute[2:]} minutes"
    if hour == "*":
        return "Every hour"
    if hour.startswith("*/"):
        return f"Every {hour[2:]} hours"
    at = f"{int(hour):02d}:{int(minute):02d}"
    if dow == "*":
        return f"Every day at {at}"
    if dow == "1-5":
        return f"Weekdays at {at}"
    if dow == "0,6":
        return f"Weekends at {at}"
    names = {n: w.capitalize() + "s" for w, n in DAY_NAMES.items()}
    days = [names[int(d)] for d in dow.split(",")]
    joined = days[0] if len(days) == 1 else ", ".join(days[:-1]) + " and " + days[-1]
    return f"{joined} at {at}"


def _hour(raw: str, minute: str | None, meridiem: str | None) -> tuple[int, int] | None:
    hour, mins = int(raw), int(minute or 0)
    half = (meridiem or "").lower().replace(".", "")
    if half == "pm" and hour < 12:
        hour += 12
    if half == "am" and hour == 12:
        hour = 0
    if hour > 23 or mins > 59:
        return None
    return hour, mins


def _time(text: str) -> tuple[int, int] | None:
    if (m := AT_TIME.search(text)) and (found := _hour(m.group(1), m.group(2), m.group(3))):
        return found
    m = BARE_TIME.search(text)
    if m and (found := _hour(m.group(1) or m.group(4), m.group(2), m.group(3) or m.group(5))):
        return found
    for word, at in PARTS_OF_DAY.items():
        if re.search(rf"\b{word}\b", text, re.I):
            return at
    return None


def _days(text: str) -> str | None:
    if WEEKDAYS.search(text):
        return "1-5"
    if WEEKENDS.search(text):
        return "0,6"
    named = sorted(n for w, n in DAY_NAMES.items() if re.search(rf"\b{w}s?\b", text, re.I))
    if named:
        return ",".join(str(n) for n in named)
    if DAILY.search(text):
        return "*"
    return None


def read(text: str) -> Schedule | None:
    """The schedule in these words, or None when they do not name one."""
    if m := EVERY_MINUTES.search(text):
        minutes = int(m.group(1))
        if 5 <= minutes < 60:
            return Schedule(f"*/{minutes} * * * *")
    if m := EVERY_HOURS.search(text):
        hours = int(m.group(1))
        if 1 <= hours < 24:
            return Schedule(f"0 */{hours} * * *" if hours > 1 else "0 * * * *")
    if m := HOURLY.search(text):
        return Schedule("0 * * * *")
    time = _time(text)
    days = _days(text)
    if time is None and days is None:
        return None
    hour, minute = time or (9, 0)
    return Schedule(f"{minute} {hour} * * {days or '*'}")
