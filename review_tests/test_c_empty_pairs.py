"""C integration regression: a valid all-rejected match has a header-only CSV."""
import csv
import json
from pathlib import Path

from mrus_missing.geometry import fit


def test_zero_accepted_pairs_produce_an_insufficient_fit(tmp_path):
    for side in ("mri", "us"):
        with (tmp_path / f"{side}_points.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["point_id", "descriptor_row", "i", "j", "k", "source_id"])
            for i, xyz in enumerate(((0, 0, 0), (2, 0, 0), (0, 2, 0), (0, 0, 2))):
                writer.writerow([f"{side}{i}", i, *xyz, "synthetic"])
    pairs = tmp_path / "pairs.csv"
    pairs.write_text("condition_id,method_id,query_id,candidate_id,d1,d2,ratio\n", encoding="utf-8")
    result = fit(pairs, tmp_path / "mri_points.csv", tmp_path / "us_points.csv",
                 Path(__file__).resolve().parents[1] / "configs/experiment-v1.json", tmp_path / "out")
    assert result["status"] == "INSUFFICIENT_MATCHES"
    transform = json.loads((tmp_path / "out/transform.json").read_text(encoding="utf-8"))
    assert transform["status"] == "INSUFFICIENT_MATCHES"
    assert transform["R"] is None and transform["t"] is None
