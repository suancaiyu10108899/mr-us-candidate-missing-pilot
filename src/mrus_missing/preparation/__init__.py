"""A owns release preparation; no research files are read by this stub."""
from pathlib import Path

from mrus_missing.errors import StageNotImplemented


def prepare(source: Path, config: Path, output: Path) -> None:
    """Reserve the source/config to immutable release interface."""
    raise StageNotImplemented("prepare", "A")
