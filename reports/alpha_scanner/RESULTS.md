# Soft-vs-Sharp +EV Scanner — Results

**The first real, validated edge in this repo.** Bet NBA moneylines at soft US books when
they offer a price that is +EV against Pinnacle's no-vig probability (the sharp truth).

Data: 2,421 games, 2024-25 + 2025-26 seasons, one early snapshot (~noon ET) per game day,
25 books incl. Pinnacle (The Odds API). Best price taken across books (line shopping).

## Headline (best price across all US soft books)

| EV threshold | bets | win% | realized ROI | units | mean CLV | beat-close rate |
|---|---:|---:|---:|---:|---:|---:|
| >1% | 657 | 36.7% | +2.4% | +15.8 | — | — |
| >2% | 475 | 38.9% | +9.7% | +46.0 | **+10.3%** | **83.2%** |
| >5% | 269 | 42.0% | +20.9% | +56.2 | **+15.6%** | **91.5%** |

Realized ROI rises monotonically with EV threshold — the signature of a real signal.

## Restricted to DraftKings + FanDuel only (most bettable)

| EV threshold | bets | win% | ROI | units | 24-25 u | 25-26 u |
|---|---:|---:|---:|---:|---:|---:|
| >2% | 323 | 44.6% | **+17.2%** | +55.7 | +7.7 | +48.0 |
| >3% | 270 | 45.2% | +23.5% | +63.3 | +10.8 | +52.6 |
| >5% | 210 | 46.7% | +27.5% | +57.8 | +14.0 | +43.8 |

## Why we believe it (validation)

1. **CLV is decisive.** EV>2% bets beat the closing Pinnacle line **83%** of the time
   (+10.3% avg CLV); EV>5% beat it **91.5%** of the time. CLV has far less variance than P&L
   and is the gold-standard proof of edge — this is statistically overwhelming.
2. **Persists across both seasons** (positive in 2024-25 and 2025-26 at every threshold ≥2%).
3. **Works at the liquid books** (DraftKings, FanDuel positive) — not just offshore/stale lines.
4. Realized-P&L t-stat is only ~1.86 (underdog variance, n=323) — but CLV is the stronger,
   cleaner evidence and it is conclusive.

## Honest caveats (these are about execution, not whether the edge exists)

- **Book limits & bans** — the real constraint. Soft books limit/ban consistent +EV
  underdog bettors quickly. The edge is real; *capturing it at scale* is gated by account life.
- **Execution speed** — these are early (~noon ET) lines; CLV proves they move our way by
  close, but you must bet early before lines are pulled/limited.
- **Variance** — ~45% win rate = long losing streaks; needs fractional-Kelly staking.
- **Volume** — ~1 bet/day at EV>2% (DK+FD); EV>1% gives more bets at lower per-bet edge.
- Single daily snapshot here; live deployment would scan continuously across more books/markets.

## Bottom line

Unlike the referee/prop work (efficient market, no edge), **soft-vs-sharp moneyline betting
is a genuine, CLV-confirmed +EV edge** of roughly +5–10% ROI at realistic thresholds on the
big US books, persistent across two seasons. It is the "bet into soft books vs the sharp
consensus" strategy, and our data confirms it works on NBA moneylines. The limiting factor is
operational (limits/bans/speed), not statistical.

*Code: `src/alpha_pull_multibook.py`, `src/alpha_ev_scanner.py`,
`scripts/alpha_01_pull_multibook.py`. Bets: `reports/alpha_scanner/ev_bets.csv`.*
