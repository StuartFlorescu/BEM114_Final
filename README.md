# BEM 114 Final Project: Referee-Aware NBA Free Throw Attempt Strategy

This repo contains our BEM 114 hedge fund final project.

## Strategy

We are studying a referee-aware NBA player free throw attempt strategy. The idea is that player free throw attempts are affected by:

- player foul-drawing ability
- projected minutes
- opponent foul tendency
- referee crew strictness
- matchup/contact environment

The goal is to build a historical signal/backtest that predicts whether a player is likely to exceed a free throw attempt line.

If we can get free historical prop odds, we will use real market lines. If not, we will use synthetic lines based on trailing player free throw attempts and clearly describe the backtest as a signal-validation backtest.

## Repo Structure

```text
config/
  settings.yaml

data/
  raw/          raw data pulled from APIs or downloaded manually
  processed/    cleaned/model-ready data
  outputs/      predictions, trades, and backtest results

notebooks/
  01_data_check.ipynb
  02_feature_exploration.ipynb
  03_results_and_charts.ipynb

src/
  pull_data.py
  build_features.py
  train_model.py
  run_backtest.py
  make_charts.py
  utils.py

scripts/
  01_pull_data.py
  02_build_features.py
  03_train_and_backtest.py
  04_make_outputs.py

reports/
  figures/
  tables/




```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Test that the environment works:

```bash
python -c "import pandas, numpy, sklearn, matplotlib, nba_api, yaml, requests; print('Environment works')"
```

## Workflow

Do not commit large raw data files or generated output files. The `.gitignore` is set up so that `data/raw`, `data/processed`, `data/outputs`, `reports/figures`, and `reports/tables` are ignored except for `.gitkeep` files.

Each person should work on their own branch and avoid pushing directly to `main`.

Suggested branch names:

```text
stuart/data-pull
partner/referee-data
partner/model-backtest
partner/report-charts
```

## Project Tasks

### Stuart / Data Pipeline

- Pull NBA player-game logs from `nba_api`
- Save raw player-game data to `data/raw/player_games.csv`
- Clean player-game data into `data/processed/player_games_clean.csv`

### Partner 1 / Referee Data

- Download or import historical referee assignment data
- Clean it into `data/processed/referee_assignments_clean.csv`
- Build referee crew strictness features

### Partner 2 / Modeling and Backtest

- Build baseline model without referees
- Add referee-aware features
- Compare baseline vs referee-aware model
- Run synthetic-line over/under backtest

### Everyone / Final Report

- Explain strategy logic
- Explain data sources
- Explain model and backtest construction
- Analyze returns and risks
- Prepare final figures and presentation slides

## First Pipeline Goal

The first real output should be:

```text
data/raw/player_games.csv
```

Then:

```text
data/processed/modeling_table.csv
```

Then:

```text
data/outputs/backtest_summary.csv
```
```
