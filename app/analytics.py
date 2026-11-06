"""Progression series and career-stat helpers for live TFRRS performances."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator, FuncFormatter

from tfrrs_client import Performance, format_mark, mark_to_seconds, seconds_to_clock


SEASON_ORDER = ("XC", "Indoor", "Outdoor")


@dataclass
class SeasonSeries:
    season_year: int
    dates: list[date]
    values: list[float]  # seconds for Time, meters/points otherwise
    marks: list[Performance]


def seasons_for(performances: list[Performance]) -> list[str]:
    found = {p.season for p in performances if p.season}
    return [s for s in SEASON_ORDER if s in found] + sorted(
        found - set(SEASON_ORDER)
    )


def events_for(performances: list[Performance], season: str) -> list[str]:
    events = sorted(
        {
            p.event_name
            for p in performances
            if p.season == season and p.event_name
        }
    )
    return events


def filter_performances(
    performances: list[Performance], season: str, event_name: str
) -> list[Performance]:
    rows = [
        p
        for p in performances
        if p.season == season and p.event_name == event_name and p.valid
    ]
    rows.sort(
        key=lambda p: (
            p.year or 0,
            p.month or 0,
            p.day or 0,
            p.meet_name,
        )
    )
    return rows


def _season_year_for(perf: Performance) -> int:
    """Map a meet date onto the collegiate season year used for coloring."""
    year = perf.year or (perf.meet_date.year if perf.meet_date else 0)
    month = perf.month or (perf.meet_date.month if perf.meet_date else 1)
    if perf.season == "XC":
        return year
    if perf.season == "Indoor":
        # Nov/Dec openers belong to the upcoming indoor season year.
        return year + 1 if month >= 11 else year
    return year


def build_series(
    performances: list[Performance], season: str, event_name: str
) -> tuple[list[SeasonSeries], str]:
    rows = filter_performances(performances, season, event_name)
    if not rows:
        return [], "Time"

    units = rows[0].units
    by_year: dict[int, list[Performance]] = defaultdict(list)
    for perf in rows:
        by_year[_season_year_for(perf)].append(perf)

    series: list[SeasonSeries] = []
    for year in sorted(by_year):
        dates: list[date] = []
        values: list[float] = []
        kept: list[Performance] = []
        for perf in by_year[year]:
            value = mark_to_seconds(perf)
            if value is None or perf.meet_date is None:
                continue
            # Plot against a shared calendar year so seasons overlay.
            overlay = _overlay_date(perf.meet_date, season, year)
            dates.append(overlay)
            values.append(value)
            kept.append(perf)
        if dates:
            series.append(
                SeasonSeries(
                    season_year=year, dates=dates, values=values, marks=kept
                )
            )
    return series, units


def _overlay_date(meet_date: date, season: str, season_year: int) -> date:
    """Shift meet dates onto a common year for month-aligned career plots."""
    if season == "Indoor" and meet_date.month >= 11:
        # Keep Nov/Dec openers just left of Jan on the shared axis.
        return date(1999, meet_date.month, meet_date.day)
    return date(2000, meet_date.month, min(meet_date.day, 28))


def personal_best(
    performances: list[Performance], season: str, event_name: str
) -> Optional[Performance]:
    rows = filter_performances(performances, season, event_name)
    if not rows:
        return None
    units = rows[0].units
    scored = [(mark_to_seconds(p), p) for p in rows if mark_to_seconds(p) is not None]
    if not scored:
        return None
    if units == "Time":
        return min(scored, key=lambda t: t[0])[1]
    return max(scored, key=lambda t: t[0])[1]


def first_year_best(
    performances: list[Performance], season: str, event_name: str
) -> Optional[Performance]:
    series, _ = build_series(performances, season, event_name)
    if not series:
        return None
    first = series[0]
    units = first.marks[0].units if first.marks else "Time"
    scored = [
        (mark_to_seconds(p), p)
        for p in first.marks
        if mark_to_seconds(p) is not None
    ]
    if not scored:
        return None
    if units == "Time":
        return min(scored, key=lambda t: t[0])[1]
    return max(scored, key=lambda t: t[0])[1]


def first_performance(
    performances: list[Performance], season: str, event_name: str
) -> Optional[Performance]:
    rows = filter_performances(performances, season, event_name)
    return rows[0] if rows else None


def improvement_seconds(
    start: Optional[Performance], best: Optional[Performance]
) -> Optional[float]:
    if not start or not best:
        return None
    a = mark_to_seconds(start)
    b = mark_to_seconds(best)
    if a is None or b is None:
        return None
    return abs(a - b)


def format_improvement(
    start: Optional[Performance], best: Optional[Performance]
) -> str:
    delta = improvement_seconds(start, best)
    if delta is None or not best:
        return "—"
    if best.units == "Time":
        return seconds_to_clock(delta)
    if best.units == "Points":
        return str(int(round(delta)))
    return f"{delta:.2f}"


def career_stats(
    performances: list[Performance], season: str, event_name: str
) -> dict[str, str]:
    pr = personal_best(performances, season, event_name)
    first_pr = first_year_best(performances, season, event_name)
    first = first_performance(performances, season, event_name)
    return {
        "personal_best": format_mark(pr) if pr else "—",
        "first_year_best": format_mark(first_pr) if first_pr else "—",
        "overall_improvement": format_improvement(first, pr),
        "first_year_improvement": format_improvement(first, first_pr),
        "result_count": str(len(filter_performances(performances, season, event_name))),
    }


YEAR_COLORS = {
    2018: "#5b6d66",
    2019: "#8a6d3b",
    2020: "#2f6f5e",
    2021: "#1f6b4f",
    2022: "#c98512",
    2023: "#0b241e",
    2024: "#3d7ea6",
    2025: "#9b4d1b",
    2026: "#12352c",
    2027: "#6b4f8a",
}


def progression_figure(
    performances: list[Performance],
    season: str,
    event_name: str,
    athlete_name: str,
) -> Optional[Figure]:
    series, units = build_series(performances, season, event_name)
    if not series:
        return None

    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=120)
    fig.patch.set_facecolor("#f7faf8")
    ax.set_facecolor("#f7faf8")

    for item in series:
        color = YEAR_COLORS.get(item.season_year, "#12352c")
        ax.plot(
            item.dates,
            item.values,
            color=color,
            marker="o",
            linewidth=2.0,
            markersize=6,
            label=f"{item.season_year}",
        )

    ax.set_title(
        f"{athlete_name} · {season} {event_name}",
        fontsize=14,
        fontweight="bold",
        color="#12352c",
        pad=12,
    )
    ax.set_xlabel("Month", color="#5b6d66")
    ylabel = {"Time": "Time", "Meters": "Meters", "Points": "Points"}.get(
        units, units
    )
    ax.set_ylabel(ylabel, color="#5b6d66")
    ax.legend(frameon=False, title="Season year")
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if season == "XC":
        ax.set_xlim(date(2000, 8, 15), date(2000, 12, 5))
    elif season == "Indoor":
        ax.set_xlim(date(1999, 11, 15), date(2000, 3, 25))
    else:
        ax.set_xlim(date(2000, 2, 20), date(2000, 7, 5))

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.xaxis.set_minor_locator(AutoMinorLocator(4))

    if units == "Time":
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda v, _pos: seconds_to_clock(float(v)))
        )
        # Faster times (lower seconds) at the top for readability.
        ax.invert_yaxis()

    fig.tight_layout()
    return fig


def results_table(
    performances: list[Performance], season: str, event_name: str
) -> dict[str, list[str]]:
    rows = filter_performances(performances, season, event_name)
    return {
        "Date": [
            p.meet_date.isoformat() if p.meet_date else "—" for p in rows
        ],
        "Mark": [format_mark(p) for p in rows],
        "Meet": [p.meet_name for p in rows],
        "Season year": [str(_season_year_for(p)) for p in rows],
    }
