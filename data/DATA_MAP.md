# Data Map

This file explains the data used in the BEM 114 final project.

## Raw Data

### data/raw/nba_2025_26_draftkings_props_with_odds.csv

Main market-pricing dataset.

Contains historical DraftKings NBA player-points props with:

- date
- player
- game
- side
- line
- american_odds

This is the most important market file because it includes both the points line and Over/Under odds.

### data/raw/nba_2025_26_draftkings_player_points_props.csv

Line-only DraftKings player-points prop file.

Useful as a coverage/reference file, but it is less important than the with-odds file because it does not include Over/Under prices.

### data/raw/player_games.csv

Raw NBA player-game logs from nba_api.

Used as the source for:

- actual points
- minutes
- field goal attempts
- FTA
- fouls drawn
- player rolling features
- team/opponent features

### data/raw/referee_games.csv

Basketball Reference referee crew data.

Contains:

- game date
- visitor team
- home team
- officials
- source URL

The referee game IDs do not match NBA API game IDs, so this file is joined by date + away team + home team.

## Processed Data

### data/processed/player_games_clean.csv

Cleaned player-game table.

Keeps the columns needed for modeling:

- player
- team
- game date
- matchup
- home/away flag
- opponent
- minutes
- FGA
- FTA
- FTM
- PFD
- PF
- TOV
- PTS

### data/processed/modeling_table.csv

Rolling feature table built from player-game logs.

Includes player and opponent features such as:

- player_pts_l5 / l10 / l20
- player_fta_l5 / l10 / l20
- player_pfd_l5 / l10 / l20
- player_min_l5 / l10 / l20
- player_fga_l5 / l10 / l20
- opp_pf_l10 / l20
- opp_fta_allowed_l10 / l20
- simple_matchup_risk

### data/processed/draftkings_player_points_clean.csv

Cleaned DraftKings market table.

This pivots separate Over/Under rows into one row per player-game-line with:

- points_line
- over_odds
- under_odds
- raw implied probabilities
- no-vig market probabilities

### data/processed/player_points_props_with_results.csv

All DraftKings market rows joined to NBA outcomes/features.

Includes both matched and unmatched rows.

### data/processed/player_points_modeling_dataset.csv

Matched rows only.

This is the first model-ready dataset with:

- market line and odds
- actual player result
- went_over / went_under / push
- rolling player features

### data/processed/player_points_modeling_dataset_with_matchups.csv

Adds defense matchup features.

Examples:

- scoring_role
- def_role_pts_allowed_l10
- def_role_fta_allowed_l10
- def_role_pfd_allowed_l10
- matchup_pts_edge_l10
- matchup_fta_edge_l10
- matchup_pfd_edge_l10

### data/processed/player_points_modeling_dataset_with_referees.csv

Adds referee crew features on top of the defense matchup dataset.

Examples:

- crew_total_pts_l20
- crew_total_fta_l20
- crew_total_pf_l20
- crew_total_pfd_l20
- ref_contact_strictness_l20
- ref_scoring_environment_l20
- player_side_ref_fta_edge_l20
- ref_contact_x_player_pfd_per_min_l10
- ref_contact_x_matchup_pfd_edge_l10

## Outputs

### data/outputs/model_predictions.csv

Model predictions for train/test rows.

Includes:

- model_prob_over
- market_prob_over_novig
- edge_over
- edge_under
- split

### data/outputs/model_metrics.csv

Model performance metrics.

Includes:

- train/test AUC
- train/test log loss
- train/test Brier score
- market comparison metrics

### data/outputs/model_coefficients.csv

Logistic regression coefficients.

Used to inspect which features push predictions toward Over or Under.

### data/outputs/trades.csv

Simulated trades from the edge-threshold backtest.

### data/outputs/backtest_summary.csv

Summary of threshold backtest performance.

## Report Files

### reports/final_numbers/FINAL_REPORT_NUMBERS.md

The clean report-ready numbers.

Use this file for the final writeup and presentation.

### reports/final_numbers/defense_only_*.csv

Final snapshots for the defense-only model.

### reports/final_numbers/referee_*.csv

Final snapshots for the defense + referee model.

## Current Final Conclusion

The broad model does not beat DraftKings overall. The strategy is strongest as a selective filter, especially in high-conviction matchup/contact-heavy situations.
