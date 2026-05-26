from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.add_matchup_features import add_defense_matchup_features

if __name__ == "__main__":
    add_defense_matchup_features()
