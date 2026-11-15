"""Date and time edges. Daylight-saving cases use the selected zone's rules."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lupaxa.data_poison.catalogue import Options, fixed, parameterised
from lupaxa.data_poison.errors import InputError

_C = "dates"


def _d(
    identifier: str,
    name: str,
    payload: str,
    validity: str,
    risk: str,
    why: str,
    contract: str = "iso-8601",
) -> None:
    fixed(
        identifier,
        category=_C,
        name=name,
        payload=payload,
        validity=validity,
        contract=contract,
        risk=risk,
        tags=("calendar",),
        explanation=why,
        intended="Calendar and clock code that only tests the middle of a month.",
    )


_d(
    "dates.leap-year",
    "Leap Day",
    "2024-02-29",
    "valid",
    "awkward",
    "2024 is a leap year, so 29 February exists.",
)
_d(
    "dates.non-leap",
    "Non-Leap February 29",
    "2023-02-29",
    "invalid",
    "hostile",
    "2023 is not a leap year.",
)
_d(
    "dates.month-boundary",
    "Month Boundary",
    "2024-01-31T23:59:60",
    "invalid",
    "awkward",
    "A leap second written as second 60. Many parsers reject it.",
)
_d(
    "dates.year-boundary",
    "Year Boundary",
    "2024-12-31T23:59:59Z",
    "valid",
    "mild",
    "The last second of a year, UTC.",
    "rfc-3339",
)
_d(
    "dates.midnight",
    "Midnight",
    "2024-01-01T00:00:00Z",
    "valid",
    "mild",
    "Midnight at the start of the civil day.",
    "rfc-3339",
)
_d(
    "dates.end-of-day",
    "End of Day",
    "2024-01-01T24:00:00",
    "valid",
    "awkward",
    "Hour 24 means the next midnight in ISO 8601. Many libraries reject it.",
)
_d(
    "dates.offset",
    "UTC Offset",
    "2024-06-01T12:00:00+01:00",
    "valid",
    "mild",
    "An explicit numeric offset.",
    "rfc-3339",
)
_d(
    "dates.fractional",
    "Fractional Seconds",
    "2024-06-01T12:00:00.123456789Z",
    "valid",
    "awkward",
    "Nanosecond fraction. Not every clock keeps that many digits.",
    "rfc-3339",
)
_d(
    "dates.bad-offset",
    "Invalid Offset",
    "2024-06-01T12:00:00+99:99",
    "malformed",
    "hostile",
    "The offset is not a real zone difference.",
    "rfc-3339",
)
_d(
    "dates.invalid-calendar",
    "Invalid Calendar Date",
    "2024-13-40",
    "invalid",
    "hostile",
    "Month 13 and day 40 do not exist.",
)
_d(
    "dates.iso-variation",
    "ISO Variation",
    "20240601T120000Z",
    "valid",
    "awkward",
    "Basic ISO 8601 without separators. RFC 3339 requires separators.",
    "iso-8601",
)
_d(
    "dates.rfc3339",
    "RFC 3339",
    "2024-06-01T12:00:00Z",
    "valid",
    "mild",
    "A common RFC 3339 timestamp.",
    "rfc-3339",
)
_d(
    "dates.epoch",
    "Unix Epoch",
    "1970-01-01T00:00:00Z",
    "valid",
    "mild",
    "Unix time zero.",
    "rfc-3339",
)
_d(
    "dates.epoch-negative",
    "Before the Epoch",
    "1969-12-31T23:59:59Z",
    "valid",
    "awkward",
    "A negative Unix timestamp.",
    "rfc-3339",
)
_d(
    "dates.huge",
    "Very Large Timestamp",
    "9999-12-31T23:59:59Z",
    "valid",
    "apocalypse",
    "The top of the common four-digit year range.",
    "rfc-3339",
)
_d("dates.date-only", "Date Only", "2024-06-01", "valid", "mild", "A calendar date with no time.")
_d("dates.time-only", "Time Only", "12:00:00", "valid", "awkward", "A time with no date.")
_d(
    "dates.bad-separator",
    "Invalid Separator",
    "2024/06/01",
    "invalid",
    "hostile",
    "Slashes are not ISO date separators.",
    "iso-8601",
)
_d(
    "dates.whitespace",
    "Unexpected Whitespace",
    "2024-06-01 12:00:00",
    "valid",
    "awkward",
    "A space instead of T. Common, and not strict RFC 3339.",
    "iso-8601",
)
_d(
    "dates.naive",
    "Naive Timestamp",
    "2024-06-01T12:00:00",
    "valid",
    "awkward",
    "No offset. The zone is unknown.",
    "iso-8601",
)
_d(
    "dates.aware",
    "Aware Timestamp",
    "2024-06-01T12:00:00+00:00",
    "valid",
    "mild",
    "An explicit zero offset.",
    "rfc-3339",
)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise InputError(
            f"timezone {name!r} is not available. "
            "Install the IANA timezone data or pick another zone."
        ) from exc


def _scan(zone_name: str, forward: bool) -> str:
    zone = _zone(zone_name)
    start = datetime(2024, 1, 1, tzinfo=zone)
    previous = start
    for hour in range(1, 24 * 370):
        current = datetime(2024, 1, 1, tzinfo=zone) + timedelta(hours=hour)
        old = previous.utcoffset() or timedelta()
        new = current.utcoffset() or timedelta()
        jumped = new - old
        if forward and jumped > timedelta(0):
            missing = (previous + timedelta(minutes=30)).replace(tzinfo=None)
            return missing.isoformat(timespec="minutes")
        if not forward and jumped < timedelta(0):
            repeated = (current - timedelta(minutes=30)).replace(tzinfo=None)
            return repeated.isoformat(timespec="minutes")
        previous = current
    raise InputError(f"{zone_name} has no {'gap' if forward else 'overlap'} in 2024.")


def _gap(rng: random.Random, options: Options) -> bytes:
    return _scan(options.timezone or "Europe/London", True).encode()


def _overlap(rng: random.Random, options: Options) -> bytes:
    return _scan(options.timezone or "America/New_York", False).encode()


parameterised(
    "dates.dst-gap",
    category=_C,
    name="Daylight-Saving Gap",
    build=_gap,
    validity="invalid",
    contract="iana-timezone",
    risk="hostile",
    tags=("dst",),
    explanation=(
        "A local time skipped when the clocks move forward in the selected zone. "
        "Default zone is Europe/London."
    ),
    intended="Local-time conversion must not invent an offset for a time that does not occur.",
)
parameterised(
    "dates.dst-overlap",
    category=_C,
    name="Daylight-Saving Overlap",
    build=_overlap,
    validity="valid",
    contract="iana-timezone",
    risk="hostile",
    tags=("dst",),
    explanation=(
        "A local time that happens twice when the clocks move back. "
        "Default zone is America/New_York."
    ),
    intended="The same wall clock can map to two UTC instants.",
)
