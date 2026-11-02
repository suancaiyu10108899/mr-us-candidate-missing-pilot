"""A's optional real-module seam tests, using only newly generated fixtures."""
import csv
import json
from pathlib import Path

import pytest

from test_preparation import source_case, prepared
from mrus_missing.capabilities import stage_capabilities
from mrus_missing.cli import main
from mrus_missing.preparation.files import digest


@pytest.mark.parametrize("method", ["MNN", "MNN_RATIO"])
def test_synthetic_match_fit_evaluate_report(source_case, method, tmp_path, capsys):
    states = stage_capabilities()
    if not all(states[stage] for stage in ("match", "fit", "evaluate", "summarize")):
        pytest.skip("requires actual B/C/D APIs in the same isolated checkout")
    prepared_result = prepared(source_case)
    release, reference = source_case["output"], source_case["reference_output"]
    protected = {p: digest(p.read_bytes()) for root in (release, reference) for p in root.iterdir()}
    predictions, evaluation, report = (tmp_path / name for name in ("predictions", "evaluation", "report"))

    def invoke(stage, **kwargs):
        args = [stage]
        for name, value in kwargs.items():
            args.extend(["--" + name.replace("_", "-"), str(value)])
        code = main(args)
        captured = capsys.readouterr()
        assert code == 0, captured.err
        return json.loads(captured.out)

    matched = invoke("match", release=release, condition_id="FULL", method_id=method,
                     expected_sha256=prepared_result["input"]["manifest_sha256"],
                     input_kind="synthetic_fixture", output=predictions,
                     run_id="synthetic-integration-" + method, operator="synthetic-test")
    assert matched["kind"] == "synthetic_fixture" and matched["accepted_count"] == 64
    fitted = invoke("fit", pairs=predictions / "pairs.csv", mri_points=release / "mri_points.csv",
                    us_points=release / "us_points.csv", config=source_case["config"],
                    output=predictions / "fit")
    assert fitted["status"] == "SUCCESS" and fitted["inlier_count"] == 64
    evaluated = invoke("evaluate", release=release, predictions=predictions,
                       reference=reference, output=evaluation)
    assert evaluated["checks_ok"] and evaluated["queries"] == 64
    with (evaluation / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        metric = next(csv.DictReader(stream))
    assert metric["N"] == metric["C"] == metric["K"] == "64"
    assert metric["false_accept_absent"] == ""
    assert metric["fit_status"] == "SUCCESS" and float(metric["probe_max"]) < 1e-10
    summary = invoke("summarize", metrics=evaluation / "metrics.csv",
                     query_evaluation=evaluation / "query_evaluation.csv", output=report)
    assert summary["rows"] == 1 and summary["queries"] == 64
    assert (report / "report.md").is_file()
    assert all(digest(path.read_bytes()) == sha for path, sha in protected.items())
