import streamlit as st

from ui_helpers import apply_theme, content_frame, page_header

apply_theme("About · TFRRS Progression")

with content_frame():
    page_header(
        "About",
        "A Streamlit rebuild of the original TFRRS Progression Visualizer, "
        "with live data instead of a static SQLite dump.",
    )

    st.markdown(
        """
        ### What changed
        - **Live TFRRS data** — teams, rosters, and athlete event histories are
          fetched on demand from [tfrrs.org](https://tfrrs.org) and cached briefly
          in Streamlit.
        - **Streamlit UI** — same visual language as the XC Race Simulator
          (pine / canopy theme, searchable pickers, metric strips).
        - **Same core views** — career progression overlays by season year, plus
          personal best / first-year best / improvement stats.

        ### How to run
        ```bash
        pip install -r requirements.txt
        cd app
        streamlit run Home.py
        ```

        ### Credits
        Original PyQt / Scrapy project by Nick Meling and Matt Egts. This fork
        keeps the progression idea and moves the front end + data layer to a
        live Streamlit workflow.
        """
    )
