"""Offline audit consistency checks; no RPC calls."""
from pathlib import Path
from flapjax_audit import validate
if __name__ == "__main__":
    validate(Path(__file__).resolve().parent)
