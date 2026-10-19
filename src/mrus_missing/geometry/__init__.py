"""C owns predicted-pair geometry. No reference transform argument."""
from pathlib import Path

from mrus_missing.errors import StageNotImplemented


def fit(pairs: Path, mri_points: Path, us_points: Path,
        config: Path, output: Path) -> None:
    """Reserve US_TO_MR fitting; no identity transform or success is fabricated."""
    raise StageNotImplemented("fit", "C")
