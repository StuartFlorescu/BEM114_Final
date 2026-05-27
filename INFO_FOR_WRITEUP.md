# INFO_FOR_WRITEUP

This file is the full writeup guide for our BEM 114 final project repo. It explains the trading strategy, the final outputs, the economic interpretation, and how the code works from start to finish.

# 1. Project Overview

Our final project is a DraftKings NBA player-points over/under strategy.

The strategy asks:

Can we use player form, defense matchup information, and referee/contact environment data to identify player-points props where DraftKings' market-implied probability is wrong?

For each player prop, we observe:

- player
- game date
- matchup
- DraftKings points line
- Over odds
- Under odds
- actual player points
- rolling player statistics
- defense matchup features
- optional referee crew features

The model estimates the probability that the player scores more than his DraftKings points line.

Then we compare that model probability to the no-vig market-implied probability from DraftKings odds.

If the model probability is sufficiently above the market probability, we bet Over.

If the model probability is sufficiently below the market probability, we bet Under.

If the model and market are close, we do not bet.

The core idea is that the strategy should not bet every prop. It should only bet when the model-market disagreement is large enough and when the matchup/contact context supports the edge.

# 2. Final Project Conclusion

The main conclusion is:

The broad model does not beat DraftKings overall. However, the model is useful as a selective high-conviction filter. The strongest evidence of edge appears in matchup/contact-heavy situations.

We should not claim that the model beats the market across the entire player-points board. It does not.

The market-implied probability is still better than our model at broadly ranking overs versus unders.

However, when we filter to specific high-conviction slices, especially defense/contact matchup slices, the strategy shows profitable test-period returns.

This gives us a more credible hedge fund-style conclusion:

The edge is concentrated, not universal.

# 3. Final Report-Ready Numbers

The final report-ready numbers are stored in:

reports/final_numbers/FINAL_REPORT_NUMBERS.md

## 3.1 Model Accuracy vs Market

Defense-only model:

- Test AUC: 0.5169
- Market test AUC: 0.5355
- Test log loss: 0.6954
- Market test log loss: 0.6915

Defense + referee model:

- Test AUC: 0.5173
- Market test AUC: 0.5355
- Test log loss: 0.6978
- Market test log loss: 0.6915

Interpretation:

- The broad defense-only model does not beat the market.
- The broad referee-enhanced model also does not beat the market.
- The market-implied probability has better AUC and better log loss than our model.
- DraftKings' prices are very hard to beat broadly.

## 3.2 Main 7.5% Edge-Threshold Strategy

Defense-only 7.5% threshold:

- 315 bets
- 11.45% of the test board
- 54.29% hit rate
- +1.81% average return per bet
- +5.70 total units

Defense + referee 7.5% threshold:

- 559 bets
- 20.32% of the test board
- 53.31% hit rate
- -0.23% average return per bet
- -1.31 total units

Interpretation:

- The defense-only 7.5% threshold is the cleanest broad profitable strategy.
- It bets only 315 of 2,751 test opportunities.
- That means it uses only 11.45% of the available board.
- The strategy earns +1.81% per bet and +5.70 units.
- The referee-enhanced broad version takes more bets but performs worse.
- Referee data does not improve the broad strategy.

## 3.3 7.5% Threshold by Over/Under

Defense-only Over bets at 7.5%:

- 66 bets
- 2.40% of the test board
- 57.58% hit rate
- +7.56% average return per bet
- +4.99 units

Defense-only Under bets at 7.5%:

- 249 bets
- 9.05% of the test board
- 53.41% hit rate
- +0.28% average return per bet
- +0.71 units

Defense + referee Over bets at 7.5%:

- 86 bets
- 3.13% of the test board
- 51.16% hit rate
- -5.07% average return per bet
- -4.36 units

Defense + referee Under bets at 7.5%:

- 473 bets
- 17.19% of the test board
- 53.70% hit rate
- +0.64% average return per bet
- +3.05 units

Interpretation:

- In the defense-only model, the profitable 7.5% strategy mainly comes from Over bets.
- Defense-only Over bets have +7.56% return per bet.
- Under bets are slightly positive but much weaker.
- After adding referee features, broad Under bets improve slightly, but broad Over bets become negative.

## 3.4 Best High-Conviction Slices

Defense-only matchup-contact slice:

- 76 bets
- 65.79% hit rate
- +23.80% average return per bet
- +18.08 total units

Defense-only matchup-points slice:

- 68 bets
- 60.29% hit rate
- +13.56% average return per bet
- +9.22 total units

Defense + referee matchup-contact slice:

- 137 bets
- 62.04% hit rate
- +16.43% average return per bet
- +22.50 total units

Defense + referee matchup-points slice:

- 167 bets
- 61.68% hit rate
- +15.53% average return per bet
- +25.93 total units

Defense + referee low-line bucket:

- 46 bets
- 69.57% hit rate
- +29.33% average return per bet
- +13.49 total units

Interpretation:

- The best strategy slices are not the broad threshold strategies.
- The strongest evidence is in high-conviction matchup/contact filters.
- Defense-only has the highest ROI in the matchup-contact slice.
- Referee-enhanced features create larger profitable slices, but they hurt the broad model.

# 4. Trading Strategy Logic

The strategy converts each DraftKings player-points market into one model row.

Each row contains:

- points line
- Over odds
- Under odds
- no-vig market probability for Over
- model probability for Over
- actual player points
- whether Over hit
- whether Under hit
- engineered player/defense/referee features

The key variables are:

- market_prob_over_novig
- model_prob_over
- edge_over
- edge_under

Definitions:

edge_over = model_prob_over - market_prob_over_novig

edge_under = market_prob_over_novig - model_prob_over

Trading rule:

- Bet Over if edge_over > threshold.
- Bet Under if edge_under > threshold.
- Otherwise no bet.

Thresholds tested:

- 2.5%
- 5.0%
- 7.5%
- 10.0%

The best broad threshold is 7.5% in the defense-only model.

This is a selective strategy. At the 7.5% threshold, the defense-only model bets only 315 out of 2,751 test opportunities, or 11.45% of the board.

# 5. Return Calculation

Each bet stakes 1 unit.

For positive American odds:

profit = odds / 100

For negative American odds:

profit = 100 / abs(odds)

If the bet loses:

return = -1

If actual points equal the line:

return = 0

In our matched player-points dataset, pushes are rare or zero because the lines are usually half-point lines such as 15.5 or 22.5.

# 6. Data Sources

## 6.1 DraftKings Player Props with Odds

File:

data/raw/nba_2025_26_draftkings_props_with_odds.csv

This is the most important market-pricing dataset.

Columns:

- date
- player
- game
- side
- line
- american_odds

This file contains separate rows for Over and Under. The code pivots it into one row per player-game-line.

The cleaned version becomes:

data/processed/draftkings_player_points_clean.csv

## 6.2 DraftKings Line-Only Props

File:

data/raw/nba_2025_26_draftkings_player_points_props.csv

This is useful for coverage/reference. It has lines but not prices, so it is less important than the with-odds dataset.

## 6.3 NBA Player Game Logs

Raw file:

data/raw/player_games.csv

Cleaned file:

data/processed/player_games_clean.csv

These contain actual NBA player-game outcomes.

Important columns:

- GAME_DATE
- GAME_ID
- PLAYER_NAME
- TEAM_ABBREVIATION
- MATCHUP
- MIN
- FGA
- FTA
- FTM
- PFD
- PF
- TOV
- PTS
- HOME
- OPP

These are used to:

- identify actual points
- label whether Over/Under hit
- build rolling player features
- build opponent/contact features

## 6.4 Referee Data

File:

data/raw/referee_games.csv

Columns:

- game_id
- game_date
- season
- visitor
- home
- matchup
- official_1
- official_2
- official_3
- official_4
- n_officials
- source_url

Important issue:

The referee file uses Basketball Reference game IDs. The NBA API uses different game IDs. So we do not join referee data by game ID.

Instead, we join by:

date + away team + home team

The referee join worked well:

- 6,140 of 6,153 referee games matched to NBA stats
- 9,413 of 9,439 prop rows matched to referee features

# 7. Full Pipeline

The intended pipeline is:

1. Clean DraftKings market data.
2. Pivot Over/Under odds into one row per player-game-line.
3. Compute no-vig market probabilities.
4. Match props to actual NBA player-game outcomes.
5. Join rolling player features.
6. Add defense matchup features.
7. Add referee crew features.
8. Train a logistic regression model.
9. Compare model probability against market probability.
10. Backtest edge-threshold betting rules.
11. Diagnose performance by side, player role, line bucket, contact bucket, matchup bucket, and other slices.
12. Preserve final report numbers.

The scripts to run are:

- python3 scripts/02_build_features.py
- python3 scripts/025_add_matchup_features.py
- python3 scripts/026_add_referee_features.py
- python3 scripts/03_train_and_backtest.py
- python3 scripts/04_make_outputs.py

# 8. Code Walkthrough

## 8.1 src/build_features.py

This is the first major feature-building script.

It does three main things:

1. Cleans the DraftKings market data.
2. Converts odds into no-vig probabilities.
3. Joins market rows to NBA outcomes and rolling features.

Important functions:

normalize_name(name)

This normalizes player names by lowercasing, removing accents, removing punctuation, removing suffixes, and applying manual aliases. This improves match quality between DraftKings and NBA game logs.

parse_prop_game(game)

DraftKings games are written like Cleveland Cavaliers @ Atlanta Hawks. This function splits the string into away team, home team, away abbreviation, and home abbreviation.

american_to_prob(odds)

Converts American odds into implied probability.

For negative odds:

prob = abs(odds) / (abs(odds) + 100)

For positive odds:

prob = 100 / (odds + 100)

clean_market_table(...)

Reads the DraftKings odds file, pivots Over and Under into one row, and computes raw probabilities, vig, and no-vig market probabilities.

prepare_modeling_table(...)

Prepares the rolling feature table for joining by date, normalized player name, away team abbreviation, and home team abbreviation.

join_props_to_features(...)

Joins cleaned DraftKings props to NBA outcomes/features and creates:

- actual_points
- went_over
- went_under
- push

Outputs:

- data/processed/player_points_props_with_results.csv
- data/processed/player_points_modeling_dataset.csv

## 8.2 src/add_matchup_features.py

This script adds defense matchup features.

The motivation is that a player-points prop depends on both the player and the opponent. Some defenses allow more points or more contact to certain types of scorers.

The script creates a scoring_role bucket based on recent scoring:

- low_usage
- rotation
- starter
- star

Then it asks:

How does this opponent perform against players in this same scoring role?

For each opponent and scoring role, the script calculates rolling defensive allowance metrics:

- def_role_pts_allowed_l10
- def_role_fta_allowed_l10
- def_role_pfd_allowed_l10
- def_role_players_faced_l10
- same metrics over 20 games

Then it creates matchup edge features:

- matchup_pts_edge_l10
- matchup_fta_edge_l10
- matchup_pfd_edge_l10
- matchup_pts_edge_l20
- matchup_fta_edge_l20
- matchup_pfd_edge_l20

Conceptually:

matchup_pts_edge_l10 = defense allowed points to similar players - player's own recent scoring baseline

Output:

data/processed/player_points_modeling_dataset_with_matchups.csv

This defense-only dataset is the cleanest broad version of the strategy.

## 8.3 src/add_referee_features.py

This script adds referee crew features.

The motivation is that referees may influence scoring environments through foul calls and free throw volume.

The script first builds game-level stats from NBA player logs:

- total points
- total FTA
- total PF
- total PFD
- home FTA edge
- home PF edge
- home points edge

Then it joins referee crews to those game stats by:

date + away team + home team

For each official, it calculates trailing historical tendencies before the current game:

- total points environment
- FTA environment
- foul environment
- fouls drawn environment
- home/away edge metrics

Then it averages the officials into crew-level features:

- crew_total_pts_l20
- crew_total_fta_l20
- crew_total_pf_l20
- crew_total_pfd_l20
- crew_home_fta_edge_l20
- crew_home_pf_edge_l20
- same metrics over 50 games
- z-score versions of these metrics

It then creates summary referee features:

- ref_contact_strictness_l20
- ref_scoring_environment_l20
- player_side_ref_fta_edge_l20
- player_side_ref_pf_edge_l20

And interaction features:

- ref_contact_x_player_pfd_per_min_l10
- ref_contact_x_player_fta_per_min_l10
- ref_contact_x_matchup_pfd_edge_l10

These interaction features ask whether a foul-drawing player benefits more when the referee crew is more contact-heavy.

Output:

data/processed/player_points_modeling_dataset_with_referees.csv

The referee data worked technically, but it did not improve the broad strategy.

## 8.4 src/train_model.py

This script trains the logistic regression model and runs the backtest.

Input:

The model dataset specified in config/settings.yaml.

Possible datasets:

- player_points_modeling_dataset.csv
- player_points_modeling_dataset_with_matchups.csv
- player_points_modeling_dataset_with_referees.csv

The script uses candidate features including:

- market probability
- points line
- recent player points
- recent player minutes
- recent FGA
- recent FTA
- recent PFD
- opponent foul/FTA allowed metrics
- defense matchup features
- referee features if present

The script automatically includes columns beginning with:

- def_role_
- matchup_
- crew_
- ref_
- player_side_ref_

So the same training code works for both defense-only and referee-enhanced datasets.

The model is:

- StandardScaler
- LogisticRegression

Target:

went_over

Train/test split:

- time-based split
- train rows before split date
- test rows on/after split date

Final split used:

- Train: 6,688 rows, 2025-12-12 to 2026-03-07
- Test: 2,751 rows, 2026-03-08 to 2026-04-10

Outputs:

- data/outputs/model_predictions.csv
- data/outputs/model_metrics.csv
- data/outputs/model_coefficients.csv

Then it calls the backtest function.

## 8.5 src/run_backtest.py

This script applies the trading rule to model predictions.

It computes:

- edge_over
- edge_under
- bet side
- per-bet return
- hit rate
- total return
- average return per bet
- number of Over bets
- number of Under bets

The script tests thresholds:

- 0.025
- 0.050
- 0.075
- 0.100

Outputs:

- data/outputs/trades.csv
- data/outputs/backtest_summary.csv

Important note:

The max_drawdown field in the main backtest summary can appear as NaN for some thresholds because of the way the equity calculation was originally defined. The diagnostic report includes a clearer unit-based drawdown calculation. This is not central to the final story.

## 8.6 src/diagnose_strategy.py

This script creates the diagnostic reports.

It groups performance by:

- threshold
- bet side
- scoring role
- points line bucket
- market probability bucket
- model edge bucket
- minutes bucket
- contact bucket
- matchup-points bucket
- matchup-contact bucket
- player

The most important diagnostic file is:

reports/tables/diagnostic_best_slices_min30.csv

The final snapshots were copied into:

reports/final_numbers/

The most important final file is:

reports/final_numbers/FINAL_REPORT_NUMBERS.md

# 9. Config File

File:

config/settings.yaml

This stores project settings and file paths.

Important field:

paths.modeling_dataset

This decides which dataset the training script uses.

For defense-only model:

data/processed/player_points_modeling_dataset_with_matchups.csv

For referee-enhanced model:

data/processed/player_points_modeling_dataset_with_referees.csv

The final numbers were produced by running both versions and copying their outputs into reports/final_numbers/.

# 10. What the Repo Currently Contains

Important docs:

- README.md
- PROJECT_STATE.md
- INFO_FOR_WRITEUP.md
- data/DATA_MAP.md

Important scripts:

- scripts/02_build_features.py
- scripts/025_add_matchup_features.py
- scripts/026_add_referee_features.py
- scripts/03_train_and_backtest.py
- scripts/04_make_outputs.py

Important source files:

- src/build_features.py
- src/add_matchup_features.py
- src/add_referee_features.py
- src/train_model.py
- src/run_backtest.py
- src/diagnose_strategy.py

Important report files:

- reports/final_numbers/FINAL_REPORT_NUMBERS.md
- reports/final_numbers/defense_only_model_metrics.csv
- reports/final_numbers/defense_only_backtest_summary.csv
- reports/final_numbers/defense_only_by_side.csv
- reports/final_numbers/defense_only_best_slices.csv
- reports/final_numbers/referee_model_metrics.csv
- reports/final_numbers/referee_backtest_summary.csv
- reports/final_numbers/referee_by_side.csv
- reports/final_numbers/referee_best_slices.csv

# 11. Writeup Language

Clean strategy paragraph:

We build a selective statistical arbitrage strategy in NBA player-points over/under markets. For each DraftKings player prop, we compute the sportsbook's no-vig implied probability and compare it to a model-implied probability based on player form, defense matchup conditions, and optional referee crew features. The strategy only trades when the model-market disagreement exceeds a fixed threshold. This makes the model a filter rather than a broad market-beating engine.

Clean result paragraph:

The market remains difficult to beat overall. In the defense-only model, test AUC is 0.5169, below the market-implied probability AUC of 0.5355. The referee-enhanced model has test AUC of 0.5173, also below the market. However, the defense-only 7.5% edge filter bets only 315 of 2,751 test opportunities, or 11.45% of the board, and earns +1.81% per bet for +5.70 total units. This indicates that the model is more useful as a selective filter than as a broad predictor.

Clean high-conviction paragraph:

The strongest results come from matchup/contact-heavy slices. The defense-only matchup-contact slice at the 7.5% threshold produces 76 bets, a 65.79% hit rate, +23.80% average return per bet, and +18.08 units. The referee-enhanced matchup-contact slice expands this to 137 bets with a 62.04% hit rate, +16.43% return per bet, and +22.50 units. This supports the idea that the edge is concentrated in specific matchup and contact environments.

# 12. Risks and Limitations

Important risks:

1. Small sample size

The broad test set has 2,751 opportunities, but the profitable slices are much smaller.

Examples:

- defense-only matchup-contact slice: 76 bets
- referee-enhanced matchup-contact slice: 137 bets
- referee-enhanced matchup-points slice: 167 bets

2. Market efficiency

DraftKings' market-implied probabilities beat our model in broad AUC.

3. Multiple testing / data mining

Because we look at many slices, some profitable slices may appear by chance.

4. Limited historical odds period

A longer historical odds dataset would be better.

5. Real-world execution

The backtest assumes quoted odds are available and executable. Real implementation would need to account for line movement, limits, timing, liquidity, account restrictions, and data latency.

6. Model simplicity

The current model is logistic regression. This is good for interpretability but may miss nonlinear interactions.

# 13. What We Should Not Claim

Do not claim:

- We beat DraftKings overall.
- The model predicts overs and unders better than the market.
- Referee data clearly improves the broad strategy.
- This is a guaranteed profitable betting system.

Correct claim:

The model does not beat the market broadly, but it identifies promising high-conviction matchup/contact slices.

# 14. Best Final Framing

Best final framing:

Our fund would not trade every NBA player-points prop. Instead, it would operate as a selective, model-driven filter. The model looks for cases where market odds disagree with player form and matchup/contact conditions. The broad strategy is only modestly profitable in the defense-only version and unprofitable after adding referee features, but the high-conviction matchup/contact slices show much stronger returns. This suggests that the strategy's edge is concentrated in specific environments rather than spread across the full betting board.

# 15. Recommended Presentation Slide Structure

1. Problem / Market
2. Strategy
3. Data
4. Feature Engineering
5. Model
6. Broad Results
7. Trading Results
8. High-Conviction Slices
9. Risks
10. Conclusion

# 16. Final One-Sentence Summary

Our model does not beat DraftKings broadly, but it can act as a selective filter that identifies profitable high-conviction player-points props in matchup/contact-heavy situations.
