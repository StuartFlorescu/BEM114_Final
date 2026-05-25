from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.train_model import main as train_main
from src.run_backtest import main as backtest_main


if __name__ == "__main__":
    train_main()
    backtest_main()
