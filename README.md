# BEM 114 Final Project: Contact-Aware NBA Player Points Prop Strategy

This repo contains our BEM 114 hedge fund final project.

We are building a sports-statistical-arbitrage strategy for NBA player points over/under markets. The core idea is to compare our model-implied probability that a player goes over his posted points line against the no-vig market-implied probability from sportsbook odds. The strategy trades only when the model-market edge is large enough.

## Strategy

The asset is an NBA player-points prop contract.

For each player-game prop, we observe:

- player
- game
- date
- DraftKings points line
- over odds
- under odds
- actual player points
- pre-game rolling basketball/contact features

The model estimates the probability that a player scores more than his posted DraftKings points line.

Basic trading rule:

- Bet Over if model_prob - market_prob > edge_threshold
- Bet Under if market_prob - model_prob > edge_threshold
- No trade otherwise

We test edge thresholds such as 2.5%, 5.0%, 7.5%, and 10.0%.

## Main Data

Final model inputs:

- data/raw/nba_2025_26_draftkings_props_with_odds.csv
- data/raw/nba_2025_26_draftkings_player_points_props.csv
- data/raw/player_games.csv
- data/processed/player_games_clean.csv
- data/processed/modeling_table.csv

The most important market dataset is:

- data/raw/nba_2025_26_draftkings_props_with_odds.csv

It contains historical DraftKings player-points lines with Over/Under sides and American odds.

## Final Pipeline

The intended final pipeline is:

1. Clean historical DraftKings props.
2. Pivot Over/Under rows into one market row per player-game-line.
3. Match each prop to NBA player-game outcomes.
4. Add actual points, went_over, went_under, and push indicators.
5. Merge pre-game rolling features.
6. Compute no-vig market-implied probabilities.
7. Train baseline model.
8. Run edge-threshold trading backtest.
9. Produce final tables and charts.

Expected processed outputs:

- data/processed/draftkings_player_points_clean.csv
- data/processed/player_points_props_with_results.csv
- data/processed/player_points_modeling_dataset.csv
- data/outputs/trades.csv

## Repo Structure

config/ contains project settings.

data/raw/ contains raw pulled or downloaded data.

data/processed/ contains cleaned and model-ready data.

data/outputs/ contains predictions, trades, backtest results, and charts.

notebooks/ contains exploratory notebooks.

scripts/ contains command-line entry points.

src/ contains project source code.

## What Is Not Part of the Final Strategy

The repo previously explored several fallback ideas and data sources. These are not part of the final model:

- synthetic free throw attempt lines
- Kalshi combo contracts
- Kaggle game-level betting data

Those files have been moved to archive/ if they existed locally.

## Project Goal

The final deliverable should show a complete historical player-points prop strategy using real DraftKings historical lines and odds, NBA player outcomes, pre-game rolling contact features, no-vig market probabilities, model probabilities, and an edge-based backtest with returns and risk statistics.
