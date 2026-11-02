"""Proper rigid motions and numerical rank in index units.

C owns this module. Every transform produced here is a proper rotation
(``det(R) == +1``) plus a translation; reflections are never returned.
No reference transform is read or stored.
"""
from __future__ import annotations

import numpy as np

FLOAT = np.float64


def rank_of(points: np.ndarray) -> int:
    """Numerical rank of centred points under the protocol tolerance.

    The protocol counts a singular value only when it is *strictly* greater
    than ``smax * max(n, 3) * float64_eps``; collinear point sets are therefore
    rank 1 and are rejected, while coplanar but non-collinear sets are rank 2
    and remain usable.
    """
    array = np.asarray(points, dtype=FLOAT)
    if array.ndim != 2 or array.shape[1] != 3 or array.shape[0] < 3:
        return 0
    if not np.isfinite(array).all():
        return 0
    centred = array - array.mean(axis=0)
    singular = np.linalg.svd(centred, compute_uv=False)
    largest = float(singular[0])
    if largest == 0.0:
        return 0
    tolerance = largest * max(array.shape[0], 3) * float(np.finfo(FLOAT).eps)
    return int(np.count_nonzero(singular > tolerance))


def fit_rigid(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares proper rigid motion mapping ``source`` onto ``target``.

    Implements the SVD (Kabsch) solution with the reflection correction that
    forces ``det(R) == +1``. Callers must check :func:`rank_of` first; this
    function only solves the algebraic problem.
    """
    src = np.asarray(source, dtype=FLOAT)
    dst = np.asarray(target, dtype=FLOAT)
    if src.shape != dst.shape or src.ndim != 2 or src.shape[1] != 3:
        raise ValueError("source and target must share shape (n, 3)")
    src_centre = src.mean(axis=0)
    dst_centre = dst.mean(axis=0)
    covariance = (src - src_centre).T @ (dst - dst_centre)
    left, _, right_t = np.linalg.svd(covariance)
    mirrored = float(np.linalg.det(right_t.T @ left.T))
    correction = np.diag([1.0, 1.0, 1.0 if mirrored >= 0.0 else -1.0])
    rotation = right_t.T @ correction @ left.T
    translation = dst_centre - rotation @ src_centre
    return rotation, translation


def apply(rotation: np.ndarray, translation: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Map row vectors with the column-vector convention ``R @ p + t``."""
    return np.asarray(points, dtype=FLOAT) @ np.asarray(rotation, dtype=FLOAT).T + translation


def residuals(rotation: np.ndarray, translation: np.ndarray,
              source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Euclidean residual per pair in index units."""
    predicted = apply(rotation, translation, source)
    return np.linalg.norm(predicted - np.asarray(target, dtype=FLOAT), axis=1)


def is_proper(rotation: np.ndarray, tolerance: float = 1e-6) -> bool:
    """Check orthonormality and ``det == +1`` within the evaluation tolerance."""
    matrix = np.asarray(rotation, dtype=FLOAT)
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        return False
    identity = np.eye(3)
    return (float(np.max(np.abs(matrix.T @ matrix - identity))) <= tolerance
            and abs(float(np.linalg.det(matrix)) - 1.0) <= tolerance)
