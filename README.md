# BEM 114 Final Project: Contact-Aware NBA Player Points Prop Strategy

This repo contains our BEM 114 hedge fund final project.

## Strategy

We are studying a sports-statistical-arbitrage strategy for NBA player points over/under markets.

The original idea was to model player free throw attempts, but free historical FTA prop lines were not available from the free API sources we tested. We therefore pivoted to real player points prop lines, which are available through The Odds API free tier.

The core idea is still contact-based: foul drawing, recent minutes, shot volume, opponent foul tendency, and opponent free throw environment may help predict whether a player goes over or under his points line.

## Current Pipeline

1. Pull NBA player-game logs from nba_api.
2. Build rolling player and opponent features.
3. Pull real player_points odds from The Odds API.
4. Convert raw sportsbook odds into clean book-level and consensus betting boards.
5. Use the feature table and real market board for model development and trade candidate analysis.

## Workflow

Build the NBA feature table:

    python scripts/01_pull_data.py
    python scripts/02_build_features.py

Pull real player points odds:

    ODDS_API_KEY="93eeb80cc7a16cdaed36e6109ba8d363" python scripts/05_pull_real_points_lines.py

Build the clean real-market board:

    python scripts/06_build_real_points_board.py

## Current Framing

This project now has two pieces:

1. Public NBA feature pipeline: player form, foul drawing, minutes, shot volume, and opponent foul environment.
2. Real sportsbook market data: player points lines and odds from multiple books.

The final model should compare our predicted probability of going over a points line against the market's no-vig implied probability.
