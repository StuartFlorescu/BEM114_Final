# 3-Season Rebuild & Out-of-Sample Validation

*Supersedes the original ~4-month (Dec 2025–Apr 2026) results. This document records
what happened when the strategy was re-tested on ~3 seasons of DraftKings odds and
stress-tested with walk-forward validation.*

## 0. What changed in the data

| Dataset | Before | After |
|---|---|---|
| DraftKings player-points odds | Dec 2025 – Apr 2026 (~4 months, 1 partial season) | **2023-24, 2024-25, 2025-26** (~3 seasons, 91k rows, 45.5k player-games) |
| NBA player game logs | partial | **5 seasons** (2021-22 → 2025-26), 131k rows |
| Referee crew data | partial | **5 seasons**, 6,150 games (aligned 1:1 with player logs) |

Player-prop odds do not exist before May 2023 on The Odds API, so 3 seasons is the
maximum obtainable. Backfill cost ~29.7k API credits; odds coverage is 99.5% of games
(the 14 missing are end-of-season games DraftKings never posted props for).

---

## 1. The headline result did not survive the larger sample

The original "profitable broad strategy" was overfit to the small, favorable test window.
On 3 seasons (time split: train 2023-10→2025-11, test 2025-11→2026-04), it flips negative.

**Defense-only, 7.5% edge threshold:**

| | Old (4-month) | New (3-season) |
|---|---:|---:|
| Bets | 315 | 232 |
| Hit rate | 54.3% | 50.9% |
| Avg return/bet | **+1.81%** | **−4.09%** |
| Total units | **+5.70** | **−9.49** |

**Every broad threshold loses money** on the larger test (units):

| Threshold | Defense-only | Defense + referee |
|---|---:|---:|
| 2.5% | −100.3 | −144.1 |
| 5.0% | −68.9 | −53.4 |
| 7.5% | −9.5 | −18.2 |
| 10% | +2.6 | −2.9 |

**Model accuracy (3-season test):** Defense-only AUC 0.529, Defense+referee 0.528 — both
still below market 0.532. The model does not beat the no-vig market price.

---

## 2. Best slices on 3 seasons (in-sample, post-hoc — hypotheses only)

The strongest concentrated slices still lean on the **contact matchup** feature
(`matchup_pfd_edge_l10`, top quartile), now over much larger samples:

| Slice | Threshold | Bets | Hit% | Return/bet | Units |
|---|---|---:|---:|---:|---:|
| matchup_contact top quartile | 2.5% | 1,365 | 54.7% | +2.8% | +38.7 |
| matchup_contact top quartile | 5.0% | 550 | 54.9% | +3.4% | +18.7 |

These were selected after seeing the data (98 slices examined), so they are inflated by
multiple-comparisons bias and treated only as hypotheses to be validated out-of-sample.

---

## 3. Frozen-rule test: train 23-24 + 24-25, test purely on 25-26

Everything frozen on train (model, top-quartile cutoff `≥0.617`, threshold picked = 7.5%),
evaluated once on untouched 2025-26.

**The frozen rule (top-quartile @ 7.5%): 217 bets, 53.5% hit, +0.38%/bet, +0.8 units — break-even.**
The train-optimal threshold (7.5%) did not transfer. But the top-vs-bottom *separation* held:

| Threshold | Top quartile | All plays | Bottom 3 quartiles |
|---|---:|---:|---:|
| 2.5% | +1.68%, +34.3u (2036) | −2.92%, −201u | −4.85%, −236u |
| 5.0% | +3.51%, +28.6u (815) | −1.30%, −29u | −4.06%, −58u |
| 7.5% | +0.38%, +0.8u (217) | +1.80%, +9.8u | +2.73%, +9.0u |

---

## 4. Walk-forward validation (13 monthly folds, expanding train)

Step month-by-month through 2024-25 and 2025-26; each fold trains on all prior data,
freezes the top-quartile cutoff on that fold's train, evaluates on the held-out month.

**Pooled out-of-sample (all folds concatenated):**

| Threshold | Top quartile (rule) | Bottom 3 quartiles | Spread |
|---|---|---|---:|
| 2.5% | +0.20%/bet, +7.0u (3,483) | −3.36%/bet, **−339u** | +3.56% |
| 5.0% | −1.02%/bet, −12.2u (1,197) | −1.33%/bet, −44u | +0.31% |
| 7.5% | +4.90%/bet, +15.1u (308) | −0.31%/bet, −2.9u | +5.22% |

**Consistency (folds where top beat bottom):** 8/13 @ 2.5%, 7/13 @ 5%, 7/8 @ 7.5%.

**Month-by-month (top quartile @ 5%)** swings violently: +10.8u (Nov'24) → −15.5u (Mar'25)
→ −9.4u (Apr'25) → +3.7u (Feb'26). No stable equity curve.

**Read:** The contact-matchup feature reliably separates good bets from bad ones
out-of-sample (the *bottom* 75% bleeds −339u at 2.5%), but the top quartile by itself is
only break-even and erratic month-to-month. The earlier in-sample +38.7u (2.5%) collapses
to +7.0u pooled — it did not generalize.

---

## 5. Filter test: does skipping bad contact matchups rescue the broad model?

Walk-forward, bottom-quartile cutoff frozen per fold; compare broad (all plays) vs filtered
(drop bottom quartile of `matchup_pfd_edge_l10`):

| Threshold | Broad (all) | Filtered (skip bottom Q) | Δ units |
|---|---:|---:|---:|
| 2.5% | −2.45%, −332u (13,575) | −2.97%, −304u (10,232) | +28.2 |
| 5.0% | −1.25%, −56.6u (4,521) | −1.48%, −48.8u (3,304) | +7.8 |
| 7.5% | +1.00%, +12.2u (1,225) | +1.63%, +13.7u (840) | +1.5 |

**Read:** Dropping only the bottom quartile trims total losses (fewer bets) but does **not**
turn the strategy profitable — per-bet return is still negative at 2.5%/5%. The middle
quartiles are also unprofitable; only the *top* quartile is okay. So the meaningful filter is
"keep only the top quartile" (= Section 4's rule, ~break-even), not "drop the worst 25%."

---

## 6. Extended test A — Referee thesis on GAME TOTALS (5,894 games, 5 seasons)

The cleanest possible test of "strict crews → more points": game totals are the high-SNR
version of the prop bet. Pulled 5 seasons of DraftKings totals odds (8.7k API credits).

- **The crew signal is real:** crew scoring environment correlates **+0.165** with the actual
  game total. Strict crews genuinely produce more scoring.
- **But the market over-prices it:** it correlates **+0.377** with the market line — *more*
  than it correlates with reality. High-crew-scoring games go OVER *less* (Q5 48.9% vs Q1 52.3%).
- **No exploitable edge out-of-sample:** season walk-forward model AUC **0.48–0.53** (coin flip);
  a contrarian "bet under on high-crew games" rule pooled **−98 units** (50.2% hit, 1/4 seasons
  positive). The market fully — even over- — prices the referee effect.

**Read:** The referee thesis is empirically true but not tradeable, confirmed on both props and
totals. Refs matter for scoring; the market knows it.

## 7. Extended test B — Low-line / low-scoring players

Hypothesis: bench/role players' low lines are thinner and softer than heavily-bet star lines.

- **Low-line is the best bucket:** at the 5% threshold it is the *only* line bucket positive
  out-of-sample (+15.7u), while mid-line loses (−53u); the edge concentrates in low-line **overs**
  (55.3% hit). Economically sensible.
- **But it does not persist:** all profit comes from 2024-25 (esp. Nov 2024 +20.5u); the entire
  **2025-26 season was flat-to-negative** across every cutoff (≤9.5/11.5/14.5) and threshold.
  Only 7/13 months positive; per-bet edge thin (+1.08%).

**Read:** The softest corner of the market, and the best candidate found — but a 2024-25
phenomenon that decayed. Not deployable; "watch with fresh data."

## 8. Overall conclusion (all tests)

- **The model does not beat DraftKings player-points markets.** Confirmed on 3 seasons;
  test AUC trails the market across every specification.
- **The original "+5.70 units / Sharpe ~3.0 slice" results were overfit** to a small, favorable
  4-month window. They do not replicate on the larger sample or out-of-sample.
- **The referee thesis is real but fully priced** — confirmed on both player props and game
  totals (game-total model is a coin flip; contrarian rule −98u).
- **Every signal found is real, economically sensible, and weak:** contact-matchup quartile
  (separates good/bad bets but only break-even), low-line overs (best bucket but decays after
  one season). None survive as a profitable, persistent edge.
- **Net:** the recurring, well-evidenced finding is that **these markets are efficient** — the
  signals exist but are priced in. The defensible result is a rigorous negative: more data +
  out-of-sample testing overturned every apparent edge, including our own headline.

*Artifacts:* `reports/final_numbers/rebuild_3season/{defense_only,referee}/`,
`data/processed/game_totals_dataset.csv`. Pipeline: `scripts/018_build_modeling_table.py` →
`02_build_features` → `025` → `026` → `03` → `04`; plus `scripts/015_merge_odds.py`,
`scripts/05c_pull_totals.py`, `src/build_totals_dataset.py`.
