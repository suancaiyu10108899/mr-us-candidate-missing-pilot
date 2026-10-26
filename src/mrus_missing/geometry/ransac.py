"""Deterministic RANSAC over accepted pairs, then one refit and re-check.

Sampling follows protocol section 6: PCG64 with the configured seed, at most
``max_iterations`` draws of ``sample_size`` pairs, best model by inlier count,
then inlier squared error, then earliest sample. The winning set is refitted
exactly once and the final inliers and both ranks are recomputed; nothing is
rescued by a second search.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .contracts import (DEGENERATE, INSUFFICIENT_MATCHES, NO_VALID_MODEL, SUCCESS,
                        require)
from .rigid import FLOAT, fit_rigid, rank_of, residuals


@dataclass
class Estimate:
    """Outcome of one US_TO_MR fit, including failed states."""

    status: str
    detail: str | None = None
    rotation: np.ndarray | None = None
    translation: np.ndarray | None = None
    residuals: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=FLOAT))
    inliers: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=bool))
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def inlier_count(self) -> int:
        return int(self.inliers.sum())


def estimate(us_points: np.ndarray, mr_points: np.ndarray,
             config: dict[str, Any]) -> Estimate:
    """Fit ``US_TO_MR`` from paired coordinates, never reading a reference."""
    src = np.asarray(us_points, dtype=FLOAT)
    dst = np.asarray(mr_points, dtype=FLOAT)
    require(src.ndim == 2 and src.shape[1] == 3, "US points must be (n, 3)")
    require(src.shape == dst.shape, "US and MR pair counts differ")
    require(bool(np.isfinite(src).all() and np.isfinite(dst).all()), "non-finite coordinate")

    count = int(src.shape[0])
    iterations = int(config["max_iterations"])
    sample_size = int(config["sample_size"])
    threshold = float(config["inlier_threshold"])
    minimum_inliers = int(config["minimum_final_inliers"])
    minimum_rank = int(config["minimum_rank"])

    diagnostics: dict[str, Any] = {
        "direction": config["direction"],
        "unit": config["unit"],
        "rng": config["rng"],
        "seed": int(config["seed"]),
        "sample_size": sample_size,
        "max_iterations": iterations,
        "inlier_threshold": threshold,
        "minimum_final_inliers": minimum_inliers,
        "minimum_rank": minimum_rank,
        "pair_count": count,
        "iterations_executed": 0,
        "valid_samples": 0,
        "degenerate_samples": 0,
        "best_sample_index": None,
        "best_inlier_count": None,
        "best_inlier_squared_error": None,
        "final_inlier_count": 0,
        "final_inlier_squared_error": None,
        "us_rank": rank_of(src),
        "mri_rank": rank_of(dst),
        "input_us_rank": rank_of(src),
        "input_mri_rank": rank_of(dst),
    }

    if count < sample_size:
        diagnostics["status_detail"] = "TOO_FEW_PAIRS"
        return Estimate(INSUFFICIENT_MATCHES, "TOO_FEW_PAIRS",
                        residuals=np.full(count, np.nan), inliers=np.zeros(count, bool),
                        diagnostics=diagnostics)

    generator = np.random.Generator(np.random.PCG64(int(config["seed"])))
    best: tuple[int, float, int, np.ndarray, np.ndarray, np.ndarray] | None = None
    executed = 0
    for iteration in range(iterations):
        executed += 1
        chosen = generator.choice(count, size=sample_size, replace=False)
        sample_us, sample_mr = src[chosen], dst[chosen]
        if rank_of(sample_us) < minimum_rank or rank_of(sample_mr) < minimum_rank:
            diagnostics["degenerate_samples"] += 1
            continue
        rotation, translation = fit_rigid(sample_us, sample_mr)
        distance = residuals(rotation, translation, src, dst)
        mask = distance <= threshold
        inlier_count = int(mask.sum())
        squared_error = float(np.square(distance[mask]).sum())
        diagnostics["valid_samples"] += 1
        if best is None:
            take = True
        else:
            take = (inlier_count > best[0]
                    or (inlier_count == best[0] and squared_error < best[1]))
        if take:
            best = (inlier_count, squared_error, iteration, rotation, translation, mask)

    diagnostics["iterations_executed"] = executed

    if best is None:
        diagnostics["us_rank"] = rank_of(src)
        diagnostics["mri_rank"] = rank_of(dst)
        if rank_of(src) < minimum_rank or rank_of(dst) < minimum_rank:
            diagnostics["status_detail"] = "ALL_SAMPLES_DEGENERATE"
            return Estimate(DEGENERATE, "ALL_SAMPLES_DEGENERATE",
                            residuals=np.full(count, np.nan), inliers=np.zeros(count, bool),
                            diagnostics=diagnostics)
        diagnostics["status_detail"] = "NO_MODEL_IN_BUDGET"
        return Estimate(NO_VALID_MODEL, "NO_MODEL_IN_BUDGET",
                        residuals=np.full(count, np.nan), inliers=np.zeros(count, bool),
                        diagnostics=diagnostics)

    inlier_count, squared_error, iteration, rotation, translation, mask = best
    diagnostics["best_sample_index"] = iteration
    diagnostics["best_inlier_count"] = inlier_count
    diagnostics["best_inlier_squared_error"] = squared_error

    # One refit on the winning inlier set, then a fresh inlier decision.
    refit_us, refit_mr = src[mask], dst[mask]
    if rank_of(refit_us) < minimum_rank or rank_of(refit_mr) < minimum_rank:
        diagnostics["status_detail"] = "REFIT_DEGENERATE"
        return Estimate(DEGENERATE, "REFIT_DEGENERATE",
                        residuals=np.full(count, np.nan), inliers=np.zeros(count, bool),
                        diagnostics=diagnostics)
    rotation, translation = fit_rigid(refit_us, refit_mr)
    distance = residuals(rotation, translation, src, dst)
    final_mask = distance <= threshold
    final_count = int(final_mask.sum())
    final_squared_error = float(np.square(distance[final_mask]).sum())
    diagnostics["final_inlier_count"] = final_count
    diagnostics["final_inlier_squared_error"] = final_squared_error
    diagnostics["us_rank"] = rank_of(src[final_mask]) if final_count else 0
    diagnostics["mri_rank"] = rank_of(dst[final_mask]) if final_count else 0

    if final_count < minimum_inliers:
        diagnostics["status_detail"] = "INSUFFICIENT_INLIERS"
        return Estimate(INSUFFICIENT_MATCHES, "INSUFFICIENT_INLIERS",
                        residuals=distance, inliers=final_mask, diagnostics=diagnostics)
    if diagnostics["us_rank"] < minimum_rank or diagnostics["mri_rank"] < minimum_rank:
        diagnostics["status_detail"] = "FINAL_RANK"
        return Estimate(DEGENERATE, "FINAL_RANK",
                        residuals=distance, inliers=final_mask, diagnostics=diagnostics)

    diagnostics["status_detail"] = None
    return Estimate(SUCCESS, None, rotation=rotation, translation=translation,
                    residuals=distance, inliers=final_mask, diagnostics=diagnostics)
