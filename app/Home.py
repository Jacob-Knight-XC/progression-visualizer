import streamlit as st

from analytics import career_stats, events_for, seasons_for
from ui_helpers import (
    apply_theme,
    athlete_selectbox,
    cached_roster,
    cached_teams,
    content_frame,
    current_division,
    gender_selector,
    load_athlete_profile,
    metric_row,
    team_selectbox,
)

apply_theme("TFRRS Progression")
div = current_division()

with content_frame():
    st.markdown(
        f"""
        <section class="xc-hero">
          <div class="xc-hero-inner">
            <div class="xc-kicker">{div['short']} · Live TFRRS</div>
            <h1 class="xc-brand">Progression<br>Visualizer</h1>
            <p class="xc-lede">
              Pull live collegiate track &amp; field and cross country history from
              TFRRS, then chart career progression and improvement by event.
              Switch division in the sidebar.
            </p>
            <div class="xc-cta-row">
              <a class="xc-cta xc-cta-primary" href="/Progression" target="_self">Open Progression</a>
              <a class="xc-cta" href="/Athlete_Stats" target="_self">Athlete Stats</a>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="xc-section">
          <h2 class="xc-section-title">Live Athlete Lookup</h2>
          <p class="xc-section-copy">
            Teams and marks are fetched on demand from tfrrs.org — no offline
            database download required.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns([1, 1.4, 1.4])
    with col_a:
        gender = gender_selector(key="home_gender")
    with col_b:
        teams = cached_teams(st.session_state["division"], gender)
        team = team_selectbox(teams, key=f"home_team_{gender}_{st.session_state['division']}")
    with col_c:
        roster = cached_roster(team["team_id"]) if team else []
        athlete = athlete_selectbox(
            roster,
            key=f"home_athlete_{team['team_id'] if team else 'none'}",
        )

    if not team:
        st.warning("Could not load teams from TFRRS. Try Refresh live data in the sidebar.")
        st.stop()
    if not athlete:
        st.info("No athletes found on this roster yet.")
        st.stop()

    profile = load_athlete_profile(athlete["profile_url"])
    seasons = seasons_for(profile.performances)
    if not seasons:
        st.info("No scored performances found for this athlete.")
        st.stop()

    # Prefer the season/event with the richest history for the home snapshot.
    best_pair = ("", "")
    best_count = -1
    for season_name in seasons:
        for event_name in events_for(profile.performances, season_name):
            count = len(
                [
                    p
                    for p in profile.performances
                    if p.season == season_name
                    and p.event_name == event_name
                    and p.valid
                ]
            )
            if count > best_count:
                best_count = count
                best_pair = (season_name, event_name)
    season, event = best_pair
    stats = (
        career_stats(profile.performances, season, event)
        if event
        else {
            "personal_best": "—",
            "first_year_best": "—",
            "overall_improvement": "—",
            "first_year_improvement": "—",
            "result_count": "0",
        }
    )

    st.markdown(
        f"""
        <div class="xc-panel">
          <strong>{profile.name}</strong>
          {" · " + profile.class_year if profile.class_year else ""}
          {" · " + profile.team_name if profile.team_name else ""}<br/>
          <span class="xc-badge">Live from TFRRS</span>
          <span class="xc-badge">{len(profile.performances)} marks</span>
          <span class="xc-badge">{", ".join(seasons)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if event:
        metric_row(
            [
                (f"PR · {season} {event}", stats["personal_best"]),
                ("1st-year best", stats["first_year_best"]),
                ("Overall improvement", stats["overall_improvement"]),
                ("Results", stats["result_count"]),
            ]
        )

    st.caption(
        "Open Progression to plot season overlays, or Athlete Stats for the full career summary."
    )
