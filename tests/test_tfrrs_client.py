"""Unit tests for mark/date parsing (no network)."""

from datetime import date

from tfrrs_client import Performance, TfrrsClient, mark_to_seconds, seconds_to_clock
from analytics import career_stats, events_for, seasons_for


def test_parse_event_header_indoor():
    event, season = TfrrsClient._parse_event_header("800 Meters (Indoor)")
    assert event == "800 Meters"
    assert season == "Indoor"


def test_parse_event_header_xc():
    event, season = TfrrsClient._parse_event_header("8k")
    assert event == "8k"
    assert season == "XC"


def test_parse_date_range():
    day, month, year = TfrrsClient._parse_date("May 21-23, 2026")
    assert (day, month, year) == (21, 5, 2026)


def test_parse_mark_time():
    parsed = TfrrsClient._parse_mark("1:52.05")
    assert parsed["valid"] is True
    assert parsed["minutes"] == 1
    assert parsed["sec_or_meters"] == 52.05
    assert parsed["units"] == "Time"


def test_parse_mark_dnf():
    parsed = TfrrsClient._parse_mark("DNF")
    assert parsed["valid"] is False


def test_seconds_to_clock():
    assert seconds_to_clock(112.05) == "1:52.05"


def test_career_stats_time_event():
    perfs = [
        Performance(
            event_name="800 Meters",
            season="Indoor",
            mark_raw="2:00.00",
            meet_name="Opener",
            meet_date=date(2024, 12, 6),
            day=6,
            month=12,
            year=2024,
            minutes=2,
            sec_or_meters=0.0,
            units="Time",
        ),
        Performance(
            event_name="800 Meters",
            season="Indoor",
            mark_raw="1:52.00",
            meet_name="Champs",
            meet_date=date(2025, 2, 28),
            day=28,
            month=2,
            year=2025,
            minutes=1,
            sec_or_meters=52.0,
            units="Time",
        ),
    ]
    assert seasons_for(perfs) == ["Indoor"]
    assert events_for(perfs, "Indoor") == ["800 Meters"]
    stats = career_stats(perfs, "Indoor", "800 Meters")
    assert stats["personal_best"] == "1:52.00"
    assert stats["result_count"] == "2"
    assert mark_to_seconds(perfs[1]) == 112.0
