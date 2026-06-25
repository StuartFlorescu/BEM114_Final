# Final Report Numbers

## 1. Model accuracy vs. market

| Version | Test AUC | Market Test AUC | Test Log Loss | Market Test Log Loss |
|---|---:|---:|---:|---:|
| Defense-only | 0.5169 | 0.5355 | 0.6954 | 0.6915 |
| Defense + referee | 0.5173 | 0.5355 | 0.6978 | 0.6915 |

Interpretation: the broad model does not beat the market overall. The market-implied probability has higher AUC than our model.

## 2. Main 7.5% edge-threshold strategy

| Version | Bets | % of Test Board | Hit Rate | Avg Return / Bet | Total Units |
|---|---:|---:|---:|---:|---:|
| Defense-only | 315 | 11.45% | 54.29% | 1.81% | 5.70 |
| Defense + referee | 559 | 20.32% | 53.31% | -0.23% | -1.31 |

Interpretation: defense-only is cleaner for the broad strategy. Referee features increase the number of bets, but broad profitability falls.

## 3. 7.5% threshold by Over/Under

| Version | Side | Bets | % of Test Board | Hit Rate | Avg Return / Bet | Total Units |
|---|---|---:|---:|---:|---:|---:|
| Defense-only | Over | 66 | 2.40% | 57.58% | 7.56% | 4.99 |
| Defense-only | Under | 249 | 9.05% | 53.41% | 0.28% | 0.71 |
| Defense + referee | Over | 86 | 3.13% | 51.16% | -5.07% | -4.36 |
| Defense + referee | Under | 473 | 17.19% | 53.70% | 0.64% | 3.05 |

Interpretation: before refs, the profitable 7.5% strategy mostly came from Overs. After refs, broad Unders improve slightly, but broad Overs worsen.

## 4. Best high-conviction slices at 7.5% threshold

### Defense-only

- Best matchup-contact slice: diagnostic_type=matchup_contact, matchup_contact_bucket=(0.65, 6.1]: 76 bets, 65.79% hit rate, 23.80% avg return/bet, 18.08 units
- Best matchup-points slice: diagnostic_type=matchup_pts, matchup_pts_bucket=(1.4, 10.45]: 68 bets, 60.29% hit rate, 13.56% avg return/bet, 9.22 units

### Defense + referee

- Best matchup-contact slice: diagnostic_type=matchup_contact, matchup_contact_bucket=(0.633, 6.1]: 137 bets, 62.04% hit rate, 16.43% avg return/bet, 22.50 units
- Best matchup-points slice: diagnostic_type=matchup_pts, matchup_pts_bucket=(-19.601000000000003, -2.5]: 167 bets, 61.68% hit rate, 15.53% avg return/bet, 25.93 units
- Best line-bucket slice: diagnostic_type=line, line_bucket=low_line: 46 bets, 69.57% hit rate, 29.33% avg return/bet, 13.49 units

## 5. Report-ready conclusion

- The broad model does not beat the market overall.
- The strategy is best used as a selective filter, not as a bet-every-edge system.
- Defense-only features give the cleaner broad profitable threshold.
- Referee features are technically well-integrated, but they do not improve the broad strategy.
- Referee-enhanced features may still help identify larger high-conviction matchup/contact slices.
- The best economic story is concentrated edge in matchup/contact-heavy situations.