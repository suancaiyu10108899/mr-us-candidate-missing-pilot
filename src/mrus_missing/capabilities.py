"""Structural API discovery; never executes a stage or reads experiment inputs.

Companion APIs distinguish delivered modules from the original callable stubs.
These names describe the C/D interfaces currently offered for integration, not
an approval of their algorithms. Keep this table and the integration guide in
sync when a module intentionally changes its public API.
"""
import importlib

from .matching_runner import matching_capabilities


def stage_capabilities() -> dict[str, bool]:
    """Report which debug entry points have their required backend APIs."""
    geometry = importlib.import_module("mrus_missing.geometry")
    evaluation = importlib.import_module("mrus_missing.evaluation")
    matching = matching_capabilities()
    # fit/evaluate/summarize alone also exist in the unimplemented bootstrap.
    fit_available = all(callable(getattr(geometry, name, None))
                        for name in ("fit", "fit_arrays", "estimate"))
    scoring_available = all(callable(getattr(evaluation, name, None))
                            for name in ("classify_query", "metrics_from_counts"))
    return {
        "prepare": True, "verify_inputs": True, "verify_reference": True,
        "package_inputs": True,
        "match": matching["match"], "match_fixture": matching["match_fixture"],
        "fit": fit_available,
        "evaluate": scoring_available and callable(getattr(evaluation, "evaluate", None)),
        "summarize": scoring_available and callable(getattr(evaluation, "summarize", None)),
        "run_matrix": False,
    }
