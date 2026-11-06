import streamlit as st

from analytics import (
    events_for,
    progression_figure,
    results_table,
    seasons_for,
)
from ui_helpers import (
    apply_theme,
    athlete_selectbox,
    cached_roster,
    cached_teams,
    content_frame,
    gender_selector,
    load_athlete_profile,
    page_header,
    show_table,
    team_selectbox,
)

apply_theme("Progression · TFRRS")

with content_frame():
    page_header(
        "Career Progression",
        "Overlay every collegiate season for one event. Marks are pulled live "
        "from the athlete’s TFRRS profile.",
    )

    col_a, col_b, col_c = st.columns([1, 1.4, 1.4])
    with col_a:
        gender = gender_selector(key="prog_gender")
    with col_b:
        teams = cached_teams(st.session_state["division"], gender)
        team = team_selectbox(
            teams, key=f"prog_team_{gender}_{st.session_state['division']}"
        )
    with col_c:
        roster = cached_roster(team["team_id"]) if team else []
        athlete = athlete_selectbox(
            roster,
            key=f"prog_athlete_{team['team_id'] if team else 'none'}",
        )

    if not team or not athlete:
        st.info("Pick a college and athlete to plot.")
        st.stop()

    profile = load_athlete_profile(athlete["profile_url"])
    seasons = seasons_for(profile.performances)
    if not seasons:
        st.warning("No valid performances found on this athlete’s TFRRS page.")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        season = st.selectbox("Season", seasons, key="prog_season")
    events = events_for(profile.performances, season)
    with c2:
        if not events:
            st.selectbox("Event", ["—"], disabled=True)
            st.stop()
        event = st.selectbox("Event", events, key=f"prog_event_{season}")

    st.session_state["selected_team_id"] = team["team_id"]
    st.session_state["selected_athlete_id"] = athlete["athlete_id"]
    st.session_state["selected_season"] = season
    st.session_state["selected_event"] = event

    fig = progression_figure(
        profile.performances, season, event, profile.name
    )
    if fig is None:
        st.info("No plottable marks for that event.")
        st.stop()

    st.pyplot(fig, clear_figure=True)
    st.markdown("#### Meet-by-meet results")
    show_table(results_table(profile.performances, season, event))
