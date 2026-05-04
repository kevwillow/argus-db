"""Pytest config: put the repo root on sys.path so `db.dedup` is importable."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
