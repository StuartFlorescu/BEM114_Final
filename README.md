# BEM 114 Final Project: NBA Player Points Prop Strategy

This repo contains our BEM 114 hedge fund final project.

We test a DraftKings NBA player-points over/under strategy. The core idea is to compare our model-implied probability that a player goes over his posted points line against the no-vig market-implied probability from DraftKings odds. We only trade when the model-market edge is large enough.

## Strategy Summary

The traded contract is an NBA player-points prop.

For each player-game prop, we observe:

- player
- game date
- matchup
- DraftKings points line
- Over odds
- Under odds
- actual player points
- rolling player features
- defense matchup features
- optional referee crew features

The model estimates the probability that a player scores more than his DraftKings points line.

Trading rule:

- Bet Over if model_prob_over - market_prob_over_novig > edge_threshold.
- Bet Under if market_prob_over_novig - model_prob_over > edge_threshold.
- No trade otherwise.

We test edge thresholds of 2.5%, 5.0%, 7.5%, and 10.0%.

## Current Pipeline

Run these scripts in order:

    python3 scripts/02_build_features.py
    python3 scripts/025_add_matchup_features.py
    python3 scripts/026_add_referee_features.py
    python3 scripts/03_train_and_backtest.py
    python3 scripts/04_make_outputs.py

## What Each Script Does

### scripts/02_build_features.py

This script:

- cleans DraftKings prop odds
- pivots Over/Under rows into one row per player-game-line
- computes no-vig market probabilities
- matches props to actual NBA player-game outcomes
- joins rolling player features

Main outputs:

- data/processed/draftkings_player_points_clean.csv
- data/processed/player_points_props_with_results.csv
- data/processed/player_points_modeling_dataset.csv

### scripts/025_add_matchup_features.py

This script adds opponent matchup features based on how defenses perform against similar scorer/contact roles.

Main output:

- data/processed/player_points_modeling_dataset_with_matchups.csv

### scripts/026_add_referee_features.py

This script adds referee crew features such as foul environment, FTA environment, scoring environment, and contact strictness.

Main output:

- data/processed/player_points_modeling_dataset_with_referees.csv

### scripts/03_train_and_backtest.py

This script:

- trains a logistic regression model
- compares model probabilities to no-vig market probabilities
- runs threshold-based backtests
- writes model metrics, predictions, trades, and summary results

Main outputs:

- data/outputs/model_predictions.csv
- data/outputs/model_metrics.csv
- data/outputs/model_coefficients.csv
- data/outputs/trades.csv
- data/outputs/backtest_summary.csv

### scripts/04_make_outputs.py

This script creates diagnostic tables by threshold, side, player role, line bucket, contact bucket, matchup bucket, and other slices.

Main outputs:

- reports/tables/
- reports/figures/
- reports/strategy_diagnostic_summary.txt

## Final Report Numbers

The clean final numbers are stored here:

- reports/final_numbers/FINAL_REPORT_NUMBERS.md

Main conclusion:

- The broad model does not beat the market overall.
- Defense-only test AUC is 0.5169 versus market test AUC of 0.5355.
- Referee-enhanced test AUC is 0.5173 versus market test AUC of 0.5355.
- The defense-only 7.5% edge filter is profitable:
  - 315 bets
  - 11.45% of the test board
  - 54.29% hit rate
  - +1.81% average return per bet
  - +5.70 units
- The broad referee-enhanced 7.5% filter is not profitable:
  - 559 bets
  - 20.32% of the test board
  - 53.31% hit rate
  - -0.23% average return per bet
  - -1.31 units
- The strongest evidence is in high-conviction matchup/contact slices.

## Final Interpretation

This is not a broad market-beating model. It is better understood as a selective filter. The model is most useful when it identifies a large model-market disagreement and the matchup/contact environment supports the edge.

Final project story:

DraftKings player-points markets are difficult to beat broadly, but edge appears concentrated in high-conviction matchup/contact situations.

## Repo Structure

- config/: project settings
- data/raw/: raw input data
- data/processed/: cleaned and model-ready data
- data/outputs/: generated model/backtest outputs
- scripts/: command-line entry points
- src/: source code
- reports/final_numbers/: final report-ready numbers
- reports/repo_health/: repo audit files

## Notes

Large local data files and generated outputs are ignored by Git where appropriate. The report-ready results are preserved in reports/final_numbers/.
