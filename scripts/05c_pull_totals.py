from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from src.pull_totals import main
if __name__ == "__main__":
    main()
