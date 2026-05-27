from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.add_referee_features import add_referee_features

if __name__ == "__main__":
    add_referee_features()
