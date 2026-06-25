"""
Scrape NBA referee assignments from Basketball-Reference.com.

For each regular-season game in the configured seasons, the script extracts the
on-court officials (typically 3, sometimes a 4th alternate) from the boxscore
page and appends a row to data/raw/referee_games.csv.

ROLE LABELS
-----------
Basketball-Reference lists officials *alphabetically by last name* on each
boxscore page and does NOT identify which official is the Crew Chief, Referee,
or Umpire. We therefore store the names in the order bbref presents them as
`official_1`, `official_2`, `official_3`, `official_4`. Treat these as
unordered crew members for modeling (each official calls fouls regardless of
role, so referee-strictness features can be built directly from names).

If true role labels are required later, cross-reference with NBA.com box scores
or the stats.nba.com `BoxScoreSummaryV2` endpoint, where the first listed
official is the Crew Chief.

USAGE
-----
    python scripts/scrape_referees.py                      # all configured seasons
    python scripts/scrape_referees.py --season 2024-25     # one season
    python scripts/scrape_referees.py --season 2024-25 --limit 50  # smoke test

The script is resumable: rerun and it will skip games already in the output CSV
or the progress file (data/raw/.referee_scrape_progress.json).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.yaml"
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_PATH = RAW_DIR / "referee_games.csv"
PROGRESS_PATH = RAW_DIR / ".referee_scrape_progress.json"

BBREF = "https://www.basketball-reference.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.0 Safari/605.1.15"
)
REQUEST_DELAY_SEC = 3.5  # bbref caps at ~20 req/min; 3.5s = ~17/min

# Last day of each regular season (inclusive). Anything after = play-in/playoffs.
REG_SEASON_LAST_DAY: dict[str, date] = {
    "2021-22": date(2022, 4, 10),
    "2022-23": date(2023, 4, 9),
    "2023-24": date(2024, 4, 14),
    "2024-25": date(2025, 4, 13),
    "2025-26": date(2026, 4, 12),
}

SCHEDULE_MONTHS = ["october", "november", "december", "january", "february", "march", "april"]


def season_end_year(season: str) -> int:
    return int(season.split("-")[0]) + 1


@dataclass
class Game:
    game_id: str          # e.g. "202312010ORL"
    game_date: date
    visitor: str
    home: str
    boxscore_url: str


@dataclass
class RefereeRow:
    game_id: str
    game_date: str        # YYYY-MM-DD
    season: str
    visitor: str
    home: str
    matchup: str          # "Washington Wizards @ Orlando Magic"
    official_1: str
    official_2: str
    official_3: str
    official_4: str       # 4th/alternate if listed, else ""
    n_officials: int
    source_url: str


class BBRefSession:
    """Polite session with global throttle and backoff on 429."""

    def __init__(self, delay: float = REQUEST_DELAY_SEC):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.delay = delay
        self._last = 0.0

    def get(self, url: str) -> requests.Response:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(4):
            try:
                resp = self.s.get(url, timeout=30)
            except requests.RequestException as e:
                print(f"  network error: {e}; retry in {2 ** attempt}s")
                time.sleep(2 ** attempt)
                continue
            self._last = time.monotonic()
            if resp.status_code in (200, 404):
                return resp
            if resp.status_code == 429:
                backoff = 60 * (attempt + 1)
                print(f"  429 rate-limited; sleeping {backoff}s")
                time.sleep(backoff)
                continue
            print(f"  HTTP {resp.status_code} for {url}; retry in {2 ** attempt}s")
            time.sleep(2 ** attempt)
        resp.raise_for_status()
        return resp


def parse_schedule_month(html: str) -> Iterator[Game]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="schedule")
    if table is None:
        return
    body = table.find("tbody") or table
    for tr in body.find_all("tr"):
        if "thead" in (tr.get("class") or []):
            continue
        date_th = tr.find("th", attrs={"data-stat": "date_game"})
        if date_th is None:
            continue
        game_id = date_th.get("csk")
        if not game_id:
            continue
        date_link = date_th.find("a")
        date_text = date_link.get_text(strip=True) if date_link else date_th.get_text(strip=True)
        try:
            game_date = datetime.strptime(date_text, "%a, %b %d, %Y").date()
        except ValueError:
            continue
        visitor_td = tr.find("td", attrs={"data-stat": "visitor_team_name"})
        home_td = tr.find("td", attrs={"data-stat": "home_team_name"})
        box_td = tr.find("td", attrs={"data-stat": "box_score_text"})
        if visitor_td is None or home_td is None or box_td is None:
            continue
        box_link = box_td.find("a")
        if box_link is None:
            continue  # future / unplayed game
        yield Game(
            game_id=game_id,
            game_date=game_date,
            visitor=visitor_td.get_text(strip=True),
            home=home_td.get_text(strip=True),
            boxscore_url=BBREF + box_link.get("href"),
        )


def parse_officials(html: str) -> list[str]:
    """Return officials in the order bbref lists them (alphabetical by last name)."""
    soup = BeautifulSoup(html, "html.parser")

    def _from_div(div) -> list[str]:
        anchors = div.find_all("a")
        if anchors:
            return [a.get_text(strip=True) for a in anchors]
        raw = div.get_text(" ", strip=True)
        raw = re.sub(r"(?i)^officials[:\s]+", "", raw)
        return [n.strip() for n in raw.split(",") if n.strip()]

    for strong in soup.find_all("strong"):
        label = strong.get_text(strip=True).rstrip(":").strip().lower()
        if label == "officials":
            names = _from_div(strong.parent)
            if names:
                return names

    # Fallback: some pages render game-info tables inside HTML comments.
    for comment in soup.find_all(string=lambda s: isinstance(s, str) and "Officials" in s):
        inner = BeautifulSoup(str(comment), "html.parser")
        for strong in inner.find_all("strong"):
            if strong.get_text(strip=True).rstrip(":").strip().lower() == "officials":
                names = _from_div(strong.parent)
                if names:
                    return names
    return []


def load_progress() -> set[str]:
    if PROGRESS_PATH.exists():
        return set(json.loads(PROGRESS_PATH.read_text()).get("completed", []))
    return set()


def save_progress(completed: set[str]) -> None:
    PROGRESS_PATH.write_text(json.dumps({"completed": sorted(completed)}, indent=2))


def existing_output_game_ids() -> set[str]:
    if not OUTPUT_PATH.exists():
        return set()
    with OUTPUT_PATH.open() as f:
        reader = csv.DictReader(f)
        return {row["game_id"] for row in reader if row.get("game_id")}


def append_rows(rows: Iterable[RefereeRow]) -> None:
    rows = list(rows)
    if not rows:
        return
    fieldnames = list(RefereeRow.__dataclass_fields__.keys())
    is_new = not OUTPUT_PATH.exists()
    with OUTPUT_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))


def iter_regular_season_games(session: BBRefSession, season: str) -> Iterator[Game]:
    end_year = season_end_year(season)
    cutoff = REG_SEASON_LAST_DAY[season]
    for month in SCHEDULE_MONTHS:
        url = f"{BBREF}/leagues/NBA_{end_year}_games-{month}.html"
        resp = session.get(url)
        if resp.status_code == 404:
            print(f"  schedule page missing (skipping): {month}")
            continue
        count = 0
        for game in parse_schedule_month(resp.text):
            if game.game_date > cutoff:
                continue
            count += 1
            yield game
        print(f"  schedule {month}: {count} regular-season games")


def scrape_season(
    session: BBRefSession,
    season: str,
    completed: set[str],
    limit: int | None = None,
) -> None:
    print(f"\n=== Season {season} ===")
    games = list(iter_regular_season_games(session, season))
    print(f"  total regular-season games found: {len(games)}")
    to_do = [g for g in games if g.game_id not in completed]
    if limit is not None:
        to_do = to_do[:limit]
    print(f"  games to scrape this run: {len(to_do)}")

    buffer: list[RefereeRow] = []
    for i, game in enumerate(to_do, 1):
        resp = session.get(game.boxscore_url)
        if resp.status_code != 200:
            print(f"  [{i}/{len(to_do)}] HTTP {resp.status_code} for {game.game_id}; skipping")
            continue
        officials = parse_officials(resp.text)
        if not officials:
            print(f"  [{i}/{len(to_do)}] no officials found for {game.game_id}")
            completed.add(game.game_id)
            continue
        padded = (officials + ["", "", "", ""])[:4]
        buffer.append(
            RefereeRow(
                game_id=game.game_id,
                game_date=game.game_date.isoformat(),
                season=season,
                visitor=game.visitor,
                home=game.home,
                matchup=f"{game.visitor} @ {game.home}",
                official_1=padded[0],
                official_2=padded[1],
                official_3=padded[2],
                official_4=padded[3],
                n_officials=len(officials),
                source_url=game.boxscore_url,
            )
        )
        completed.add(game.game_id)
        if i % 25 == 0 or i == len(to_do):
            print(f"  [{i}/{len(to_do)}] {game.game_id} ({game.game_date}): {len(officials)} officials")
            append_rows(buffer)
            buffer = []
            save_progress(completed)

    append_rows(buffer)
    save_progress(completed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape NBA referee assignments from bbref.")
    parser.add_argument(
        "--season",
        action="append",
        help="Season slug, e.g. 2024-25. Repeatable. Defaults to seasons in config/settings.yaml.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max games to scrape per season this run (useful for smoke-testing).",
    )
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    seasons = args.season or config.get("seasons") or list(REG_SEASON_LAST_DAY)
    unknown = [s for s in seasons if s not in REG_SEASON_LAST_DAY]
    if unknown:
        raise SystemExit(
            f"Unknown season(s): {unknown}. Add a regular-season cutoff in "
            f"REG_SEASON_LAST_DAY to enable them."
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    completed = load_progress() | existing_output_game_ids()
    print(f"Resuming with {len(completed)} games already scraped")
    print(f"Output: {OUTPUT_PATH}")

    session = BBRefSession()
    for season in seasons:
        scrape_season(session, season, completed, limit=args.limit)
    print("\nDone.")


if __name__ == "__main__":
    main()
