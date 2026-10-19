"""Weekday numbers mean what cron means: 0 is Sunday, 1-5 is Monday to Friday.

APScheduler alone reads them from Monday = 0, which made every "weekdays" routine fire Tuesday to
Saturday.
"""

from __future__ import annotations

from datetime import UTC, datetime

from server.agents import scheduler, when


def fires(cron: str, count: int) -> list[str]:
    trigger = scheduler.trigger(cron)
    at = datetime(2026, 10, 17, 12, tzinfo=UTC)  # a Saturday
    days = []
    for _ in range(count):
        found = trigger.get_next_fire_time(None, at)
        assert found is not None
        days.append(found.strftime("%a"))
        at = found.replace(second=1)
    return days


def test_weekdays_are_monday_to_friday() -> None:
    assert fires("0 7 * * 1-5", 5) == ["Mon", "Tue", "Wed", "Thu", "Fri"]
    assert fires("0 7 * * 0", 1) == ["Sun"]
    assert fires("0 7 * * 7", 1) == ["Sun"]
    assert fires("0 7 * * 0,6", 2) == ["Sun", "Sat"]
    assert fires("0 7 * * mon-fri", 1) == ["Mon"]
    assert scheduler.validate_cron("0 7 * * 9")


def test_schedules_are_read_from_plain_words() -> None:
    cases = {
        "every weekday at 7am check the ES range": ("0 7 * * 1-5", "Weekdays at 07:00"),
        "Every morning, summarise my notes": ("0 8 * * *", "Every day at 08:00"),
        "on mondays and fridays at 5:30pm back up": (
            "30 17 * * 1,5",
            "Mondays and Fridays at 17:30",
        ),
        "every 15 minutes check the garage door": ("*/15 * * * *", "Every 15 minutes"),
        "weekends at noon": ("0 12 * * 0,6", "Weekends at 12:00"),
        "every 3 hours": ("0 */3 * * *", "Every 3 hours"),
    }
    for text, (cron, said) in cases.items():
        found = when.read(text)
        assert found is not None, text
        assert (found.cron, found.said) == (cron, said), text
    assert when.read("summarise my inbox") is None
