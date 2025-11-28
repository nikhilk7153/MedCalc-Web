from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
CALC_DIR = BASE_DIR / "calculator_implementations"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if CALC_DIR.exists() and str(CALC_DIR) not in sys.path:
    sys.path.insert(0, str(CALC_DIR))

__all__ = ["BASE_DIR", "CALC_DIR"]

