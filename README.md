# TFRRS Progression Visualizer

Streamlit app that pulls **live** collegiate track & field and cross country
history from [TFRRS](https://tfrrs.org) and charts an athlete’s career
progression by event.

This is a modernization of the original PyQt5 / Scrapy project: the offline
`ncaa.db` download is no longer required. Teams, rosters, and marks are fetched
on demand (with short Streamlit caches). The UI matches the look of the related
[XC Race Simulator](https://github.com/Jacob-Knight-XC/Race-Simulator).

## What you can do

| Page | Purpose |
|------|---------|
| **Home** | Live athlete lookup + quick PR / improvement snapshot |
| **Progression** | Season-overlaid career plot for one event + meet table |
| **Athlete Stats** | Personal best, first-year best, overall & first-year improvement |
| **About** | Background and run instructions |

Sidebar controls:

- College division (NCAA DI / DII / DIII / NAIA)
- **Refresh live data** to clear cached TFRRS responses

## Setup

```bash
pip install -r requirements.txt
cd app
streamlit run Home.py
```

`runtime.txt` pins **Python 3.12** for Streamlit Community Cloud. Prefer 3.11–3.12
locally as well.

## Project layout

```
app/                 Streamlit app (run from here)
  Home.py            Landing page + live athlete lookup
  tfrrs_client.py    Live TFRRS HTTP client (teams / roster / history)
  analytics.py       Progression series, PRs, improvement, matplotlib chart
  ui_helpers.py      Theme, pickers, cached loaders
  pages/             Progression / Stats / About
tfrrs/               Original Scrapy spider + PyQt desktop app (legacy)
```

## Legacy desktop app

The original PyQt visualizer and Scrapy crawler still live under `tfrrs/`. They
expected a large `ncaa.db` that was removed from git. Prefer the Streamlit app
above for day-to-day use.

## Credits

Original project by Nick Meling and Matt Egts. Streamlit + live-data rebuild
for this fork.
