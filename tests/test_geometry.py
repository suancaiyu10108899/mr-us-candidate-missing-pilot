"""C's artificial-fit tests. Every case is synthetic; no research data is read."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pytest

from mrus_missing.cli import main
from mrus_missing.geometry import fit_arrays, fit
from mrus_missing.geometry.contracts import GEOMETRY_V1, load_geometry_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiment-v1.json"


def rotation(axis, angle):
    """Rodrigues rotation with det(R) == +1."""
    unit = np.asarray(axis, dtype=np.float64)
    unit = unit / np.linalg.norm(unit)
    cross = np.array([[0.0, -unit[2], unit[1]],
                      [unit[2], 0.0, -unit[0]],
                      [-unit[1], unit[0], 0.0]])
    return np.eye(3) + math.sin(angle) * cross + (1.0 - math.cos(angle)) * (cross @ cross)


def write_points(path: Path, identifiers, coordinates) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, lineterminator="\n",
            fieldnames=["point_id", "descriptor_row", "i", "j", "k", "source_id"])
        writer.writeheader()
        for row, identifier in enumerate(identifiers):
            i, j, k = (float(value) for value in coordinates[row])
            writer.writerow({"point_id": identifier, "descriptor_row": row,
                             "i": repr(i), "j": repr(j), "k": repr(k), "source_id": identifier})


def write_pairs(path: Path, pairs) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, lineterminator="\n",
            fieldnames=["condition_id", "method_id", "query_id", "candidate_id", "d1", "d2", "ratio"])
        writer.writeheader()
        for query, candidate, d1 in pairs:
            writer.writerow({"condition_id": "FULL", "method_id": "MNN", "query_id": query,
                             "candidate_id": candidate, "d1": repr(float(d1)), "d2": "",
                             "ratio": ""})


@pytest.fixture
def published(tmp_path):
    """Four non-coplanar US points and one exactly consistent rigid motion."""
    rng = np.random.default_rng(11)
    us = rng.uniform(2.0, 60.0, size=(4, 3))
    matrix = rotation([0.3, -0.7, 0.5], 0.9)
    translation = np.array([2.5, -1.25, 4.0])
    mri = us @ matrix.T + translation
    directory = tmp_path / "case"
    directory.mkdir()
    pairs_path = directory / "pairs.csv"
    write_points(directory / "us_points.csv", [f"u{i}" for i in range(4)], us)
    write_points(directory / "mri_points.csv", [f"q{i}" for i in range(4)], mri)
    write_pairs(pairs_path, [(f"q{i}", f"u{i}", 0.0) for i in range(4)])
    return {"directory": directory, "us": us, "mri": mri, "R": matrix, "t": translation}


def run_fit(directory: Path, output: Path):
    return fit(directory / "pairs.csv", directory / "mri_points.csv",
               directory / "us_points.csv", CONFIG, output)


def read_transform(output: Path) -> dict:
    return json.loads((output / "transform.json").read_text(encoding="utf-8"))


def test_recovers_nonzero_rotation_and_translation(published, tmp_path):
    result = run_fit(published["directory"], tmp_path / "out")
    transform = read_transform(tmp_path / "out")
    assert result["status"] == "SUCCESS"
    matrix = np.asarray(transform["R"], dtype=np.float64)
    translation = np.asarray(transform["t"], dtype=np.float64)
    assert np.allclose(matrix, published["R"], atol=1e-9)
    assert np.allclose(translation, published["t"], atol=1e-9)
    assert transform["direction"] == "US_TO_MR" and transform["unit"] == "index_unit"
    assert transform["fit_config"]["seed"] == 20261005
    assert len(transform["pairs_sha256"]) == 64 and len(transform["source_commit"]) == 40


def test_transform_matrix_is_orthonormal_and_proper(published, tmp_path):
    run_fit(published["directory"], tmp_path / "out")
    matrix = np.asarray(read_transform(tmp_path / "out")["R"], dtype=np.float64)
    assert np.max(np.abs(matrix.T @ matrix - np.eye(3))) <= 1e-6
    assert abs(np.linalg.det(matrix) - 1.0) <= 1e-6
    assert np.isfinite(matrix).all()


def test_cli_fit_writes_three_artefacts(published, tmp_path, capsys):
    output = tmp_path / "runs"
    code = main(["fit", "--pairs", str(published["directory"] / "pairs.csv"),
                 "--mri-points", str(published["directory"] / "mri_points.csv"),
                 "--us-points", str(published["directory"] / "us_points.csv"),
                 "--config", str(CONFIG), "--output", str(output)])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "SUCCESS"
    assert {p.name for p in output.iterdir()} == {"transform.json", "inliers.csv", "fit_diagnostics.json"}
    rows = list(csv.DictReader((output / "inliers.csv").read_text(encoding="utf-8").splitlines()))
    assert [row["query_id"] for row in rows] == ["q0", "q1", "q2", "q3"]
    assert all(row["inlier"] == "true" and float(row["residual"]) <= 1.0 for row in rows)


def test_rigid_fit_never_returns_a_reflection():
    """A mirror image gets a proper rotation with large residuals, never det -1."""
    tetrahedron = np.array([[1.0, 1.0, 1.0], [1.0, -1.0, -1.0],
                            [-1.0, 1.0, -1.0], [-1.0, -1.0, 1.0]]) * 25 + np.array([30.0, 30.0, 30.0])
    mirrored = tetrahedron * np.array([-1.0, 1.0, 1.0]) + np.array([2.0, 1.0, 3.0])
    from mrus_missing.geometry.rigid import fit_rigid, residuals
    matrix, translation = fit_rigid(tetrahedron, mirrored)
    assert abs(np.linalg.det(matrix) - 1.0) <= 1e-6
    assert np.min(residuals(matrix, translation, tetrahedron, mirrored)) > 1.0


def test_reflected_correspondences_do_not_become_success(tmp_path):
    """A chiral configuration cannot be explained by any proper rotation."""
    tetrahedron = np.array([[1.0, 1.0, 1.0], [1.0, -1.0, -1.0],
                            [-1.0, 1.0, -1.0], [-1.0, -1.0, 1.0]]) * 25 + np.array([30.0, 30.0, 30.0])
    mirrored = tetrahedron * np.array([-1.0, 1.0, 1.0]) + np.array([2.0, 1.0, 3.0])
    write_points(tmp_path / "us_points.csv", [f"u{i}" for i in range(4)], tetrahedron)
    write_points(tmp_path / "mri_points.csv", [f"q{i}" for i in range(4)], mirrored)
    write_pairs(tmp_path / "pairs.csv", [(f"q{i}", f"u{i}", 0.0) for i in range(4)])
    result = run_fit(tmp_path, tmp_path / "out")
    assert result["status"] == "INSUFFICIENT_MATCHES"
    assert result["inlier_count"] < 4
    transform = read_transform(tmp_path / "out")
    assert transform["R"] is None and transform["t"] is None


def test_reflection_outliers_are_not_inliers(published, tmp_path):
    """Four proper pairs plus two reflected pairs: only the proper ones survive."""
    us = np.vstack([published["us"], np.array([[10.0, 20.0, 30.0], [40.0, 5.0, 25.0]])])
    reflected = (np.array([[10.0, 20.0, 30.0], [40.0, 5.0, 25.0]]) * np.array([-1.0, 1.0, 1.0])
                 + np.array([3.0, 1.0, 2.0]))
    mri = np.vstack([published["mri"], reflected])
    directory = tmp_path / "reflection"
    directory.mkdir()
    write_points(directory / "us_points.csv", ["u0", "u1", "u2", "u3", "u4", "u5"], us)
    write_points(directory / "mri_points.csv", ["q0", "q1", "q2", "q3", "q4", "q5"], mri)
    write_pairs(directory / "pairs.csv", [(f"q{i}", f"u{i}", 0.0) for i in range(6)])
    result = run_fit(directory, tmp_path / "out")
    assert result["status"] == "SUCCESS"
    assert result["inlier_count"] == 4
    matrix = np.asarray(read_transform(tmp_path / "out")["R"], dtype=np.float64)
    assert abs(np.linalg.det(matrix) - 1.0) <= 1e-6
    flags = {row["query_id"]: row["inlier"] for row in
             csv.DictReader((tmp_path / "out" / "inliers.csv").read_text(encoding="utf-8").splitlines())}
    assert flags["q4"] == "false" and flags["q5"] == "false"
    assert all(flags[f"q{i}"] == "true" for i in range(4))


def test_collinear_points_are_degenerate(tmp_path):
    steps = np.array([[0.0, 0.0, 0.0], [3.0, 1.0, 2.0], [6.0, 2.0, 4.0],
                      [9.0, 3.0, 6.0], [12.0, 4.0, 8.0]])
    mri = steps @ rotation([1.0, 0.0, 0.0], 0.4).T + np.array([1.0, 2.0, 3.0])
    write_points(tmp_path / "us_points.csv", [f"u{i}" for i in range(5)], steps)
    write_points(tmp_path / "mri_points.csv", [f"q{i}" for i in range(5)], mri)
    write_pairs(tmp_path / "pairs.csv", [(f"q{i}", f"u{i}", 0.0) for i in range(5)])
    result = run_fit(tmp_path, tmp_path / "out")
    assert result["status"] == "DEGENERATE"
    diagnostics = json.loads((tmp_path / "out" / "fit_diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["degenerate_samples"] == diagnostics["max_iterations"] == 256
    assert read_transform(tmp_path / "out")["R"] is None


def test_coplanar_but_not_collinear_is_accepted(tmp_path):
    base = np.array([[0.0, 0.0, 5.0], [10.0, 0.0, 5.0], [0.0, 10.0, 5.0],
                     [10.0, 10.0, 5.0], [4.0, 7.0, 5.0]])
    matrix = rotation([0.0, 0.0, 1.0], 0.35)
    mri = base @ matrix.T + np.array([-2.0, 3.0, 1.0])
    write_points(tmp_path / "us_points.csv", [f"u{i}" for i in range(5)], base)
    write_points(tmp_path / "mri_points.csv", [f"q{i}" for i in range(5)], mri)
    write_pairs(tmp_path / "pairs.csv", [(f"q{i}", f"u{i}", 0.0) for i in range(5)])
    result = run_fit(tmp_path, tmp_path / "out")
    assert result["status"] == "SUCCESS"
    assert result["inlier_count"] == 5


def test_fewer_than_four_pairs_is_insufficient(tmp_path):
    us = np.array([[1.0, 2.0, 3.0], [5.0, 1.0, 4.0], [2.0, 6.0, 0.5]])
    mri = us + np.array([1.0, -1.0, 2.0])
    write_points(tmp_path / "us_points.csv", ["u0", "u1", "u2"], us)
    write_points(tmp_path / "mri_points.csv", ["q0", "q1", "q2"], mri)
    write_pairs(tmp_path / "pairs.csv", [(f"q{i}", f"u{i}", 0.0) for i in range(3)])
    result = run_fit(tmp_path, tmp_path / "out")
    assert result["status"] == "INSUFFICIENT_MATCHES"
    assert read_transform(tmp_path / "out")["R"] is None


def test_three_consistent_pairs_among_outliers_is_insufficient(tmp_path):
    rng = np.random.default_rng(3)
    us = rng.uniform(5.0, 60.0, size=(5, 3))
    mri = us + np.array([1.0, 2.0, -3.0])
    mri[3] = [0.0, 0.0, 0.0]
    mri[4] = [60.0, 60.0, 60.0]
    write_points(tmp_path / "us_points.csv", [f"u{i}" for i in range(5)], us)
    write_points(tmp_path / "mri_points.csv", [f"q{i}" for i in range(5)], mri)
    write_pairs(tmp_path / "pairs.csv", [(f"q{i}", f"u{i}", 0.0) for i in range(5)])
    result = run_fit(tmp_path, tmp_path / "out")
    assert result["status"] == "INSUFFICIENT_MATCHES"
    assert result["status_detail"] == "INSUFFICIENT_INLIERS"
    assert result["inlier_count"] < 4


def test_same_seed_is_reproducible(published, tmp_path):
    run_fit(published["directory"], tmp_path / "a")
    run_fit(published["directory"], tmp_path / "b")
    first = read_transform(tmp_path / "a")
    second = read_transform(tmp_path / "b")
    assert first["R"] == second["R"] and first["t"] == second["t"]
    assert (tmp_path / "a" / "fit_diagnostics.json").read_text(encoding="utf-8") == \
           (tmp_path / "b" / "fit_diagnostics.json").read_text(encoding="utf-8")


def test_unknown_candidate_is_rejected(published, tmp_path):
    (published["directory"] / "pairs.csv").unlink()
    write_pairs(published["directory"] / "pairs.csv", [("q0", "missing", 0.0)])
    with pytest.raises(ValueError):
        run_fit(published["directory"], tmp_path / "out")


def test_existing_output_directory_is_not_overwritten(published, tmp_path):
    (tmp_path / "out").mkdir()
    with pytest.raises(ValueError):
        run_fit(published["directory"], tmp_path / "out")


def test_geometry_block_must_match_protocol():
    changed = json.loads(CONFIG.read_text(encoding="utf-8"))
    changed["geometry"]["inlier_threshold"] = 2.0
    with pytest.raises(ValueError):
        load_geometry_config(changed)


def test_inliers_never_exceed_threshold(published, tmp_path):
    run_fit(published["directory"], tmp_path / "out")
    diagnostics = json.loads((tmp_path / "out" / "fit_diagnostics.json").read_text(encoding="utf-8"))
    assert diagnostics["residual_summary"]["inlier_max"] <= GEOMETRY_V1["inlier_threshold"]
    assert diagnostics["status"] == "SUCCESS"
    assert diagnostics["final_inlier_count"] == 4
