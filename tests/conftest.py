# Ensure tests can import the top-level module when running from repo root
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
