"""D owns reference-based scoring and result explanation."""
from pathlib import Path

from mrus_missing.errors import StageNotImplemented


def evaluate(release: Path, predictions: Path, reference: Path, output: Path) -> None:
    """Reserve independent scoring; this is the only stage accepting reference."""
    raise StageNotImplemented("evaluate", "D")


def summarize(metrics: Path, query_evaluation: Path, output: Path) -> None:
    """Reserve report production from verified outputs."""
    raise StageNotImplemented("summarize", "D")
