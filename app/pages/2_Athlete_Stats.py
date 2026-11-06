import streamlit as st

from analytics import career_stats, events_for, seasons_for
from ui_helpers import (
    apply_theme,
    athlete_selectbox,
    cached_roster,
    cached_teams,
    content_frame,
    gender_selector,
    load_athlete_profile,
    metric_row,
    page_header,
    team_selectbox,
)

apply_theme("Athlete Stats · TFRRS")

with content_frame():
    page_header(
        "Athlete Stats",
        "Career personal best, first-year best, and improvement — the same "
        "summary view from the original desktop app, now fed by live TFRRS data.",
    )

    col_a, col_b, col_c = st.columns([1, 1.4, 1.4])
    with col_a:
        gender = gender_selector(key="stats_gender")
    with col_b:
        teams = cached_teams(st.session_state["division"], gender)
        team = team_selectbox(
            teams, key=f"stats_team_{gender}_{st.session_state['division']}"
        )
    with col_c:
        roster = cached_roster(team["team_id"]) if team else []
        athlete = athlete_selectbox(
            roster,
            key=f"stats_athlete_{team['team_id'] if team else 'none'}",
        )

    if not team or not athlete:
        st.info("Pick a college and athlete.")
        st.stop()

    profile = load_athlete_profile(athlete["profile_url"])
    seasons = seasons_for(profile.performances)
    if not seasons:
        st.warning("No valid performances found on this athlete’s TFRRS page.")
        st.stop()

    # Prefer the event already chosen on the Progression page when possible.
    preferred_season = st.session_state.get("selected_season")
    season_index = (
        seasons.index(preferred_season) if preferred_season in seasons else 0
    )
    c1, c2 = st.columns(2)
    with c1:
        season = st.selectbox(
            "Season", seasons, index=season_index, key="stats_season"
        )
    events = events_for(profile.performances, season)
    with c2:
        if not events:
            st.selectbox("Event", ["—"], disabled=True)
            st.stop()
        preferred_event = st.session_state.get("selected_event")
        event_index = (
            events.index(preferred_event) if preferred_event in events else 0
        )
        event = st.selectbox(
            "Event", events, index=event_index, key=f"stats_event_{season}"
        )

    stats = career_stats(profile.performances, season, event)

    st.markdown(
        f"""
        <div class="xc-panel">
          <strong>{profile.name}'s career stats in the {season} {event}</strong><br/>
          <span class="xc-badge">{profile.team_name or team["name"]}</span>
          {"<span class='xc-badge'>" + profile.class_year + "</span>" if profile.class_year else ""}
          <span class="xc-badge">Live TFRRS</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_row(
        [
            ("Personal best", stats["personal_best"]),
            ("1st-year best", stats["first_year_best"]),
            ("Overall improvement", stats["overall_improvement"]),
            ("1st-year improvement", stats["first_year_improvement"]),
        ]
    )

    st.caption(
        f"{stats['result_count']} valid marks used. Improvement is the absolute "
        "gap from the athlete’s first mark to their best (or first-year best)."
    )
