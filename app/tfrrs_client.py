"""Live TFRRS HTTP client — teams, rosters, and athlete event histories."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://tfrrs.org"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# NCAA / NAIA league index pages on TFRRS
DIVISIONS = {
    "d1": {"label": "NCAA Division I", "short": "DI", "league_id": 49},
    "d2": {"label": "NCAA Division II", "short": "DII", "league_id": 50},
    "d3": {"label": "NCAA Division III", "short": "DIII", "league_id": 51},
    "naia": {"label": "NAIA", "short": "NAIA", "league_id": 53},
}
DIVISION_ORDER = ("d3", "d1", "d2", "naia")
DEFAULT_DIVISION = "d3"

INVALID_MARKS = {"ND", "NT", "NH", "DNF", "FOUL", "DNS", "DQ", "SCR", "FS", "NM"}
MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
XC_EVENT_RE = re.compile(r"^\d+(\.\d+)?k$", re.IGNORECASE)


@dataclass(frozen=True)
class Team:
    name: str
    team_id: str
    gender: str
    division: str


@dataclass(frozen=True)
class Athlete:
    athlete_id: int
    name: str  # "First Last"
    last_first: str  # "Last, First"
    team_id: str
    profile_url: str


@dataclass
class Performance:
    event_name: str
    season: str  # XC | Indoor | Outdoor
    mark_raw: str
    meet_name: str
    meet_date: Optional[date]
    day: Optional[int]
    month: Optional[int]
    year: Optional[int]
    minutes: Optional[int] = None
    sec_or_meters: Optional[float] = None
    units: str = "Time"  # Time | Meters | Points
    wind_legal2: int = 1
    wind_legal4: int = 1
    valid: bool = True


@dataclass
class AthleteProfile:
    athlete_id: int
    name: str
    team_name: str
    class_year: str
    profile_url: str
    performances: list[Performance] = field(default_factory=list)


class TfrrsClient:
    """Thin requests + BeautifulSoup wrapper around public TFRRS pages."""

    def __init__(self, session: Optional[requests.Session] = None, timeout: int = 30):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = timeout

    def _get(self, url: str) -> BeautifulSoup:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def fetch_teams(self, division: str, gender: str) -> list[Team]:
        meta = DIVISIONS[division]
        url = f"{BASE_URL}/leagues/{meta['league_id']}.html"
        soup = self._get(url)
        teams: list[Team] = []
        seen: set[str] = set()

        for row in soup.select("div.col-lg-4 table tbody tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            col = cols[0] if gender == "m" else cols[1]
            link = col.find("a", href=True)
            if not link:
                continue
            name = link.get_text(strip=True)
            href = link["href"]
            team_id = href.rstrip("/").split("/")[-1].replace(".html", "")
            if not name or team_id in seen:
                continue
            seen.add(team_id)
            teams.append(
                Team(name=name, team_id=team_id, gender=gender, division=division)
            )

        teams.sort(key=lambda t: t.name.lower())
        return teams

    def fetch_roster(self, team_id: str) -> list[Athlete]:
        # TF roster is broader; athlete pages still carry XC history.
        url = f"{BASE_URL}/teams/tf/{team_id}.html"
        soup = self._get(url)
        athletes: list[Athlete] = []
        seen: set[int] = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/athletes/" not in href:
                continue
            text = link.get_text(" ", strip=True)
            if "," not in text:
                continue
            last, first = [part.strip() for part in text.split(",", 1)]
            if not last or not first:
                continue
            try:
                athlete_id = int(href.strip("/").split("/")[-3])
            except (IndexError, ValueError):
                continue
            if athlete_id in seen:
                continue
            seen.add(athlete_id)
            profile = href if href.startswith("http") else urljoin(BASE_URL, href)
            if not profile.endswith(".html"):
                profile = profile.rstrip("/") + ".html"
            athletes.append(
                Athlete(
                    athlete_id=athlete_id,
                    name=f"{first} {last}",
                    last_first=f"{last}, {first}",
                    team_id=team_id,
                    profile_url=profile,
                )
            )

        athletes.sort(key=lambda a: a.last_first.lower())
        return athletes

    def fetch_athlete(self, profile_url: str) -> AthleteProfile:
        if not profile_url.startswith("http"):
            profile_url = urljoin(BASE_URL, profile_url)
        if not profile_url.endswith(".html"):
            profile_url = profile_url.rstrip("/") + ".html"

        soup = self._get(profile_url)
        athlete_id = int(profile_url.strip("/").split("/")[-3])

        heading = soup.select_one(".panel-heading")
        heading_text = heading.get_text(" ", strip=True) if heading else ""
        h3 = soup.select_one("h3")
        display = h3.get_text(" ", strip=True) if h3 else heading_text
        # e.g. "NATHAN AHERN (SO-2)" → title case name + class
        class_year = ""
        name = display
        match = re.match(r"^(.*?)(?:\s*\(([^)]+)\))?\s*$", display)
        if match:
            name = " ".join(match.group(1).split()).title()
            class_year = (match.group(2) or "").strip()

        team_name = ""
        if heading_text:
            # "NAME (CLASS) TEAM"
            leftover = heading_text
            if name.upper() in leftover.upper():
                leftover = re.sub(re.escape(name), "", leftover, flags=re.I)
            leftover = re.sub(r"\([^)]*\)", "", leftover).strip()
            team_name = " ".join(leftover.split()).title()

        performances = self._parse_event_history(soup)
        return AthleteProfile(
            athlete_id=athlete_id,
            name=name,
            team_name=team_name,
            class_year=class_year,
            profile_url=profile_url,
            performances=performances,
        )

    def _parse_event_history(self, soup: BeautifulSoup) -> list[Performance]:
        section = soup.select_one("#event-history")
        if not section:
            return []

        performances: list[Performance] = []
        for table in section.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            header = " ".join(rows[0].stripped_strings).replace("Top↑", "").strip()
            event_name, season = self._parse_event_header(header)
            if not event_name:
                continue
            for row in rows[1:]:
                cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) < 3:
                    continue
                mark_raw, meet_name, date_raw = cells[0], cells[1], cells[-1]
                day, month, year = self._parse_date(date_raw)
                meet_date = (
                    date(year, month, day)
                    if day and month and year
                    else None
                )
                parsed = self._parse_mark(mark_raw)
                performances.append(
                    Performance(
                        event_name=event_name,
                        season=season,
                        mark_raw=mark_raw.strip(),
                        meet_name=meet_name.strip(),
                        meet_date=meet_date,
                        day=day,
                        month=month,
                        year=year,
                        minutes=parsed["minutes"],
                        sec_or_meters=parsed["sec_or_meters"],
                        units=parsed["units"],
                        wind_legal2=parsed["wind_legal2"],
                        wind_legal4=parsed["wind_legal4"],
                        valid=parsed["valid"],
                    )
                )
        return performances

    @staticmethod
    def _parse_event_header(header: str) -> tuple[str, str]:
        cleaned = re.sub(r"\s+", " ", header).strip()
        if not cleaned:
            return "", ""
        season_match = re.search(r"\((Indoor|Outdoor|XC)\)", cleaned, re.I)
        if season_match:
            season = season_match.group(1).title()
            if season.lower() == "xc":
                season = "XC"
            event_name = re.sub(r"\((Indoor|Outdoor|XC)\)", "", cleaned, flags=re.I)
            event_name = event_name.strip(" ,")
            return event_name, season
        # XC distances are labeled "8k" / "6k" without a season tag.
        if XC_EVENT_RE.match(cleaned.replace(" ", "")):
            return cleaned.replace(" ", "").lower(), "XC"
        return cleaned, "Outdoor"

    @staticmethod
    def _parse_date(raw: str) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """Parse TFRRS dates like 'Jan 17, 2026' or 'May 21-23, 2026'."""
        if not raw:
            return None, None, None
        text = " ".join(raw.split())
        match = re.search(
            r"([A-Za-z]{3})\s+(\d{1,2})(?:\s*-\s*(?:[A-Za-z]{3}\s+)?\d{1,2})?,\s*(\d{4})",
            text,
        )
        if not match:
            return None, None, None
        month = MONTHS.get(match.group(1).lower()[:3])
        day = int(match.group(2))
        year = int(match.group(3))
        return day, month, year

    @staticmethod
    def _parse_mark(mark: str) -> dict:
        original = mark.strip()
        result = {
            "minutes": None,
            "sec_or_meters": None,
            "units": "Time",
            "wind_legal2": 1,
            "wind_legal4": 1,
            "valid": True,
        }
        if not original or original.upper() in INVALID_MARKS:
            result["valid"] = False
            return result

        text = original
        if "W" in text:
            text = text.replace("W", "")
            result["wind_legal2"] = 0
            result["wind_legal4"] = 0
        elif "w" in text:
            text = text.replace("w", "")
            result["wind_legal2"] = 0

        # Field / multi events: distance ends with m, points are large ints.
        if text.endswith("m") and ":" not in text:
            try:
                result["sec_or_meters"] = float(text[:-1])
                result["units"] = "Meters"
                return result
            except ValueError:
                result["valid"] = False
                return result

        minutes = None
        seconds_part = text
        if ":" in text:
            left, right = text.split(":", 1)
            try:
                minutes = int(left)
            except ValueError:
                result["valid"] = False
                return result
            seconds_part = right

        try:
            seconds = float(seconds_part)
        except ValueError:
            result["valid"] = False
            return result

        # Heuristic from the original project: large "time" values are points.
        if minutes is None and seconds >= 100 and "." not in seconds_part:
            result["sec_or_meters"] = seconds
            result["units"] = "Points"
            return result

        result["minutes"] = minutes
        result["sec_or_meters"] = seconds
        result["units"] = "Time"
        return result


def format_mark(perf: Performance) -> str:
    """Human-readable mark string."""
    if not perf.valid or perf.sec_or_meters is None:
        return perf.mark_raw
    if perf.units == "Meters":
        return f"{perf.sec_or_meters:.2f}m"
    if perf.units == "Points":
        return str(int(perf.sec_or_meters))
    total = (perf.minutes or 0) * 60 + perf.sec_or_meters
    return seconds_to_clock(total)


def seconds_to_clock(total_seconds: float) -> str:
    if total_seconds is None:
        return "—"
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    if hours:
        return f"{sign}{hours}:{minutes:02d}:{seconds:05.2f}"
    if minutes:
        return f"{sign}{minutes}:{seconds:05.2f}"
    return f"{sign}{seconds:.2f}"


def mark_to_seconds(perf: Performance) -> Optional[float]:
    if not perf.valid or perf.sec_or_meters is None:
        return None
    if perf.units != "Time":
        return float(perf.sec_or_meters)
    return (perf.minutes or 0) * 60 + perf.sec_or_meters
