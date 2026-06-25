# BEM 114 — Presentation (16 slides)
**Referee-Aware NBA Player Points Prop Strategy**

*Updated after 3-season backfill + out-of-sample validation. Drop each slide's content into your deck. Speaker notes are in italics under each slide.*

---

## Slide 1 — Title

**Can You Beat the NBA Player-Points Market?**
A referee-aware model, honestly stress-tested on 3 seasons

BEM 114 Final Project
[Team names]
[Date]

*Speaker notes: The honest hook — "We built a referee-aware model, found a profitable-looking edge, then got more data and out-of-sample tested it. Here's what held up and what didn't." This is a research-integrity story.*

---

## Slide 2 — Executive Summary

**Thesis**
Stricter referee crews call more fouls → more free-throw attempts → higher scoring → exploitable edge on player-points "overs."

**Approach**
Logistic regression predicting `P(player exceeds line)`, using player form, defensive matchups, and a novel **referee crew strictness feature**. Benchmarked against the no-vig market price.

**Headline result (after validation)**
- Broad model **does not beat the market** (3-season test AUC 0.529 vs market 0.532).
- An early "profitable slice" result (Sharpe ~3) **was overfit** — it did not survive 3 seasons or out-of-sample testing.
- The one durable finding: a **contact-matchup feature** separates good bets from bad ones out-of-sample — a useful **filter**, not a money-maker.

*Speaker notes: Lead with humility. The value here is the rigor: we overturned our own headline with more data. That IS the result.*

---

## Slide 3 — Strategy Thesis: Why Refs Might Matter

**The causal chain**
```
Strict referee crew → more fouls called → higher FTA
→ inflated player point totals → edge on "over" side
(props priced before the crew is known)
```

**Why this could be alpha (and not already priced)**
- Prop markets are **thin** vs game lines — books invest less in sharpening them.
- Referee assignments post ~90 min before tip; the wider market doesn't fully re-price for crew strictness.
- Foul-rate variation across crews is real and persistent.

*Speaker notes: The mechanism is plausible. The empirical question is whether it's big enough to beat the vig — and the answer turned out to be mostly no.*

---

## Slide 4 — Data Stack

| Source | What | Volume | How |
|---|---|---:|---|
| **Basketball-Reference** | Referee crews per game | 6,150 games × 3 refs, 5 seasons | Custom Python scraper, 3.5 s throttle |
| **DraftKings** (via The Odds API) | Player-points lines + O/U odds | **91k rows, 3 seasons (2023-24 → 2025-26)** | Historical snapshot API, ~30 min pre-tip |
| **NBA Stats (`nba_api`)** | Player game logs (PTS, FTA, PF, PFD, MIN) | 131k player-games, 5 seasons | Official NBA REST endpoint |

**Key upgrade:** odds backfilled from 1 partial season (~4 months) to **3 full seasons**, tripling the backtestable sample. Player-prop odds don't exist before May 2023, so 3 seasons is the ceiling.

*Speaker notes: The 3-season odds backfill (29.7k API credits, 99.5% coverage) is what made honest validation possible — the original 4-month sample was too small to trust.*

---

## Slide 5 — Feature Engineering: Referee Crew Strictness

**Per-official rolling stats (20- and 50-game windows)** — for each referee, leak-free rolling means of: fouls called, free-throw attempts, fouls drawn, home–away foul differential.

**Crew aggregation** — average the 3 officials' rolling stats → per-crew z-scores vs league baseline.

**Composite features**
```
ref_contact_strictness  = mean(z_total_fta, z_total_pf, z_total_pfd)
ref_scoring_environment = z_total_pts
ref_home_fta_bias       = z_home_minus_away_fta_edge
```
**Interactions:** `ref_contact_strictness × player_pfd_per_min_l10`.

*Speaker notes: The novel piece — treat each official as a time series, aggregate per crew. It's well-engineered; it just didn't move the needle on returns.*

---

## Slide 6 — Feature Engineering: Player & Matchup

**Player (rolling 5/10/20 games):** pts/min, FTA/min, PFD/min, projected minutes, scoring role.
**Opponent / matchup:** opponent FTA & fouls allowed; `matchup_pts_edge`; **`matchup_pfd_edge`** (player contact rate vs opponent contact allowed) — *this becomes the one feature that survives validation.*
**Market:** no-vig implied probability — the benchmark to beat.

*Speaker notes: Flag matchup_pfd_edge here; it's the protagonist of the validation slides.*

---

## Slide 7 — Modeling Approach

**Target:** `went_over` (binary). **Model:** logistic regression (interpretable, low overfit risk).
**Two specs:** (1) Defense-only, (2) Defense + referee.
**Split:** time-based, no look-ahead. **Betting rule:** bet when `|model_prob − market_prob_novig| ≥ τ`, for τ ∈ {2.5%, 5%, 7.5%, 10%}.

*Speaker notes: Time-based split is essential. We later go further — full walk-forward — because a single split can still flatter you.*

---

## Slide 8 — Backtest Methodology

**Conventions:** 1 unit per bet, real DraftKings American odds, push = refund, no Kelly/sizing (pure signal eval). Vig (~4.5% at −110) is the implicit transaction cost; the no-vig market price is the null model.

**Validation ladder (this is the point):**
1. Single time split (train early → test late)
2. Frozen-rule test (train 2 seasons → test the 3rd, nothing tuned on test)
3. **Walk-forward** (13 monthly folds, expanding train) — the real test of stability

*Speaker notes: Each rung is stricter. An edge that survives walk-forward is believable; one that only shows up in a single split usually isn't.*

---

## Slide 9 — Headline Result: The Edge Did Not Survive More Data

**Defense-only, 7.5% edge — same strategy, bigger sample:**

| | Original (4-month) | Rebuilt (3-season) |
|---|---:|---:|
| Bets | 315 | 232 |
| Hit rate | 54.3% | 50.9% |
| Avg return/bet | **+1.81%** | **−4.09%** |
| Total units | **+5.70** | **−9.49** |

**Every broad threshold now loses** (total units):

| τ | Defense-only | Defense + referee |
|---|---:|---:|
| 2.5% | −100.3 | −144.1 |
| 5.0% | −68.9 | −53.4 |
| 7.5% | −9.5 | −18.2 |
| 10% | +2.6 | −2.9 |

Test AUC 0.529 (def-only) / 0.528 (+ref) vs **market 0.532** — model never beats the price.

*Speaker notes: This is the turn. The original positive result was a small-sample artifact. We know because we went and got 3 seasons.*

---

## Slide 10 — Why It Looked Good Before: Overfitting

**The original "high-conviction slices"** (62–70% hit, Sharpe ~3) came from:
- A **single 4-month test window** (one favorable stretch of one season)
- **Post-hoc slicing**: ~100 buckets examined, the best few reported
- Bucket edges computed **using the test data itself** (look-ahead in the cut)

**On 3 seasons, the same matchup-contact slice:**

| | Original (in-sample) | Pooled walk-forward |
|---|---:|---:|
| matchup_contact top quartile @ 2.5% | +38.7 units | **+7.0 units** |

The number didn't disappear entirely — but it shrank ~5× and stopped being reliable.

*Speaker notes: Three classic overfitting traps, all present. Multiple-comparisons + tiny sample + leakage in the bucket definition. The honest fix is out-of-sample testing.*

---

## Slide 11 — Out-of-Sample Validation: Walk-Forward

**13 monthly folds, expanding train, everything frozen per fold (model + quartile cutoff).**

Pooled out-of-sample, top vs bottom contact-matchup quartile:

| τ | Top quartile (rule) | Bottom 3 quartiles | Spread |
|---|---|---|---:|
| 2.5% | +0.20%/bet, +7.0u (3,483) | −3.36%/bet, **−339u** | +3.56% |
| 5.0% | −1.02%/bet, −12.2u | −1.33%/bet, −44u | +0.31% |
| 7.5% | +4.90%/bet, +15.1u (308) | −0.31%/bet, −2.9u | +5.22% |

**Consistency:** top beat bottom in 8/13, 7/13, 7/8 folds. **Month-to-month:** swings +10.8u → −15.5u → +3.7u — no stable equity curve.

*Speaker notes: The signal is the SEPARATION — the bottom 75% bleeds −339u while the top is flat. The feature flags bad bets reliably; it just doesn't make the good ones profitable.*

---

## Slide 12 — The One Real Signal: A Filter, Not a System

**Can the contact-matchup feature rescue the broad model?** Walk-forward, drop the worst bets:

| τ | Broad (all plays) | Keep top quartile only |
|---|---:|---:|
| 2.5% | −2.45%/bet, −332u | +0.20%/bet, **+7.0u** |
| 5.0% | −1.25%/bet, −56.6u | −1.02%/bet, −12.2u |
| 7.5% | +1.00%/bet, +12.2u | +4.90%/bet, +15.1u |

**Takeaway:** filtering to favorable contact matchups turns a heavily losing book into roughly **break-even** — real risk reduction, but not positive expectancy you can bank on. As a standalone money-maker, it fails.

*Speaker notes: This is the honest "so what." The feature has genuine out-of-sample value as a −EV filter. It is not a profitable strategy. Don't oversell it.*

---

## Slide 13 — Extended Validation: Totals & Low-Line

We stress-tested the thesis two more ways. Both reinforce "efficient market."

**A. Referee thesis on GAME TOTALS** (5,894 games, 5 seasons — the high-SNR version of the bet)
- Crew scoring environment correlates **+0.165 with the actual total** (real) but **+0.377 with the market line** (priced — *over*-priced).
- High-crew-scoring games go OVER *less*. Walk-forward model AUC **0.48–0.53** (coin flip); contrarian rule **−98 units**. → Refs are real but fully priced on totals too.

**B. Low-line / role-player props** (are thin markets softer?)
- Low-line is the **best bucket** — only one positive out-of-sample at 5% (+15.7u), edge in low-line *overs* (55.3%).
- But it **doesn't persist**: all profit from 2024-25; **2025-26 flat-to-negative**; 7/13 months positive. → Best candidate found, but decayed after one season.

*Speaker notes: Two more honest swings. The totals test is the cleanest possible referee test and the market wins. Low-line is the softest corner and the most promising — but it doesn't survive into the latest season. Same lesson everywhere.*

---

## Slide 14 — Risks & Limitations

**Statistical**
- Even 3 seasons = ~2.5 seasons of out-of-sample months; per-bet binary variance is high.
- Multiple-testing risk is the central lesson — the original slices were mined.
- Walk-forward profitability is threshold-sensitive and month-to-month erratic.

**Market structure**
- Vig (~4.5%) is a hard hurdle the model clears in accuracy but not in P&L.
- Closing-line value not measured; sportsbook prop limits cap scale.

**Data**
- Referee features are backward-looking (rolling means lag regime changes).
- Odds are DraftKings-only; player-prop history starts May 2023 (3-season ceiling).

*Speaker notes: The headline limitation became the headline finding: small samples manufacture fake edges. We caught ours.*

---

## Slide 15 — What We'd Do Next

- **More folds / books:** add sportsbooks and a 4th season as it accrues to firm up the contact-matchup signal.
- **Use the feature as a filter,** not a generator — layer it on a model that already has independent edge.
- **Measure CLV** to see if the model has edge vs the *opening* line that the closing line erodes.
- **Pre-register** the rule before testing the next season — no peeking, no re-tuning.

*Speaker notes: The mechanism is plausible enough to keep watching, but the bar is "survives pre-registered out-of-sample," which we now respect.*

---

## Slide 16 — Conclusion

**What we built**
- End-to-end pipeline: ref scraping → features → model → backtest → walk-forward validation.
- Novel referee crew strictness feature, no commercial data dependency.
- 3-season odds backfill enabling honest evaluation.

**What we found**
- ❌ The model **does not beat** the DraftKings player-points market (AUC 0.529 vs 0.532).
- ❌ The original "+5.70 units / Sharpe ~3 slices" headline **was overfit** — it didn't replicate.
- ❌ The referee thesis is **real but fully priced** — confirmed on game totals too (model is a coin flip, contrarian rule −98u).
- 〰️ Every signal we found is real, sensible, and **weak**: contact-matchup separates good/bad bets (break-even); low-line overs are the softest market (but decayed after one season). None persist as profit.

**The real takeaway**
More data + out-of-sample testing overturned a confident-looking result. That's the project: an efficient market, an honest negative, and one small signal that survived scrutiny.

*Speaker notes: End on research integrity. "We tried to beat an efficient market, mostly couldn't, and proved it on ourselves." That's a stronger story than a fake Sharpe of 3.*

---

## Appendix — Numbers Cheat Sheet (for Q&A)

**3-season rebuild (test 2025-11 → 2026-04), 7.5% edge**

| Metric | Defense-only | Def + referee |
|---|---:|---:|
| Bets | 232 | 432 |
| Hit rate | 50.9% | 50.9% |
| Avg return/bet | −4.09% | −4.22% |
| Total units | −9.49 | −18.24 |
| Test AUC | 0.529 | 0.528 |
| Market test AUC | 0.532 | 0.532 |

**Walk-forward (13 folds), top contact-matchup quartile, pooled out-of-sample**

| τ | Bets | Hit% | Ret/bet | Units | Bottom-75% units |
|---|---:|---:|---:|---:|---:|
| 2.5% | 3,483 | 53.5% | +0.20% | +7.0 | −339 |
| 5.0% | 1,197 | 52.9% | −1.02% | −12.2 | −44 |
| 7.5% | 308 | 56.2% | +4.90% | +15.1 | −2.9 |

**Data volumes:** 6,150 referee-games (5 seasons) · 91k DraftKings prop rows (3 seasons) · 131k player-games (5 seasons) · break-even hit at −110: 52.4% · vig ~4.5%.

*Full detail: `reports/final_numbers/REBUILD_3SEASON_RESULTS.md`.*
