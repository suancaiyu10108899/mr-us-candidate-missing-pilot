"""Descriptor-only production API and the reserved legacy CLI shell."""
from pathlib import Path

from mrus_missing.errors import StageNotImplemented

from .core import l2_distances, match_descriptors, match_inputs
from .outputs import write_match_outputs


def match(mri_descriptors: Path, us_descriptors: Path, conditions: Path,
          condition_id: str, method_id: str, output: Path) -> None:
    """Legacy CLI reservation; A must update its bootstrap contract before wiring."""
    raise StageNotImplemented("match", "B")

__all__ = ["match", "l2_distances", "match_descriptors", "match_inputs", "write_match_outputs"]
