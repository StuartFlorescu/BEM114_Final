# Current Project State

## Final strategy

We are testing a DraftKings NBA player-points over/under strategy. The model predicts the probability that a player goes over his posted DraftKings points line, compares that probability to the no-vig market-implied probability, and only bets when the model-market edge is large.

## Current pipeline

1. `scripts/02_build_features.py`
   - Cleans DraftKings prop odds.
   - Pivots Over/Under rows into one market row.
   - Joins props to NBA outcomes and rolling player features.

2. `scripts/025_add_matchup_features.py`
   - Adds defense matchup features.
   - Measures how opponents perform against similar scorer/contact roles.

3. `scripts/026_add_referee_features.py`
   - Adds referee crew strictness and contact/scoring environment features.
   - Joins referee data by date + away team + home team.

4. `scripts/03_train_and_backtest.py`
   - Trains the baseline logistic model.
   - Compares model probability to no-vig market probability.
   - Runs edge-threshold backtests.

5. `scripts/04_make_outputs.py`
   - Produces diagnostic tables and strategy summaries.

## Final report numbers

Use:

`reports/final_numbers/FINAL_REPORT_NUMBERS.md`

Key conclusions:

- The broad model does not beat the market overall.
- Defense-only test AUC: 0.5169.
- Referee-enhanced test AUC: 0.5173.
- Market test AUC: 0.5355.
- Defense-only 7.5% edge filter: 315 bets, 11.45% of board, 54.29% hit rate, +1.81% return per bet, +5.70 units.
- Defense + referee broad 7.5% filter: 559 bets, 20.32% of board, 53.31% hit rate, -0.23% return per bet, -1.31 units.
- Best defense-only matchup-contact slice: 76 bets, 65.79% hit rate, +23.80% return per bet, +18.08 units.
- Best referee-enhanced matchup-contact slice: 137 bets, 62.04% hit rate, +16.43% return per bet, +22.50 units.
- Best referee-enhanced matchup-points slice: 167 bets, 61.68% hit rate, +15.53% return per bet, +25.93 units.

## Final story

The strategy is not a broad market-beater. It is best understood as a selective high-conviction filter. The strongest evidence is concentrated in matchup/contact-heavy situations.
