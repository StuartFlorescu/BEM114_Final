# NBA Betting Research — Two Projects, Shared Data

This repo holds **two separate research projects** that share the same data and
infrastructure. They are kept apart so each tells its own story.

```
├── config/                 SHARED  project settings (seasons, paths, thresholds)
├── data/                   SHARED  raw/, processed/, outputs/  (NBA logs, odds, referees)
├── src/                    code modules  (shared pullers + per-project logic)
├── scripts/                CLI entrypoints
└── reports/
    ├── referee_strategy/   PROJECT 1 outputs + writeups
    └── alpha_scanner/      PROJECT 2 outputs + writeups
```

---

## Shared infrastructure (used by both projects)

**Data acquisition** (`src/` + `scripts/`):
- `01_pull_data` — NBA player game logs via `nba_api` (5 seasons)
- `scrape_referees` — Basketball-Reference referee crews
- `05_pull_real_points_lines` / `05b_pull_historical_points_lines` — DraftKings player-points odds (The Odds API)
- `05c_pull_totals` — DraftKings game-total odds (bulk featured market)
- `015_merge_odds` — merge odds files into one market table

**Data** (`data/raw`, `data/processed`, `data/outputs`) and **config** (`config/settings.yaml`)
are shared by both projects.

Secrets: `ODDS_API_KEY` lives in `.env.local` (gitignored). Use the project venv `.venv`.

---

## Project 1 — Referee-Aware Player-Points Prop Strategy *(academic / BEM 114)*

Can a referee-aware model beat the DraftKings player-points market? **Conclusion: no** —
the market is efficient; signals are real but priced in (see writeup).

- **Code:** `018_build_modeling_table`, `02_build_features`, `025_add_matchup_features`,
  `026_add_referee_features`, `03_train_and_backtest`, `04_make_outputs`,
  `src/build_totals_dataset.py` (referee→totals test)
- **Run:** `018 → 02 → 025 → 026 → 03 → 04`
- **Writeups:** [`reports/referee_strategy/final_numbers/REBUILD_3SEASON_RESULTS.md`](reports/referee_strategy/final_numbers/REBUILD_3SEASON_RESULTS.md)
  (validated results) and [`reports/referee_strategy/PRESENTATION_15_SLIDES.md`](reports/referee_strategy/PRESENTATION_15_SLIDES.md).
  Older docs (`FINAL_REPORT_NUMBERS.md`, `PROJECT_STATE.md`, `INFO_FOR_WRITEUP.md`) are
  pre-rebuild and **superseded**.

## Project 2 — Soft-vs-Sharp +EV Scanner *(alpha hunting)*

Stop trying to out-predict the market; exploit its **microstructure** instead. Treat the
sharp consensus (Pinnacle / market median) as "true" probability and find soft US books
(DraftKings, etc.) offering +EV prices. Validate with **Closing Line Value (CLV)**, not noisy P&L.

- **Code:** `src/alpha_*.py`, `scripts/alpha_*.py`
- **Outputs/writeups:** `reports/alpha_scanner/`
- Status: in progress.
