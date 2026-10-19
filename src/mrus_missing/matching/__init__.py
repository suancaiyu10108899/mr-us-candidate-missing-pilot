"""B owns descriptor-only prediction. No coordinates or reference argument."""
from pathlib import Path

from mrus_missing.errors import StageNotImplemented


def match(mri_descriptors: Path, us_descriptors: Path, conditions: Path,
          condition_id: str, method_id: str, output: Path) -> None:
    """Reserve queries/pairs/diagnostics production; perform no matching yet."""
    raise StageNotImplemented("match", "B")
