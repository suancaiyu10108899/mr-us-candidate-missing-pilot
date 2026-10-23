import copy
import inspect
import json
from pathlib import Path

import pytest

from mrus_missing.cli import main, run_matrix
from mrus_missing.contracts import inspect_fixture, validate_fixture
from mrus_missing.errors import StageNotImplemented
from mrus_missing.evaluation import evaluate, summarize
from mrus_missing.geometry import fit
from mrus_missing.matching import match

FIXTURE = Path(__file__).parent / "fixtures" / "interface-v1.json"


@pytest.fixture
def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_roundtrip_and_row_order(sample):
    result = inspect_fixture(FIXTURE)
    shuffled = copy.deepcopy(sample)
    shuffled["mri"]["points"].reverse()
    shuffled["us"]["points"].reverse()
    assert validate_fixture(shuffled) == result
    assert result["kept_ids_in_source_order"] == ["u17", "u23", "u11"]
    assert result["scientific_result"] is False
    assert result["algorithm_executed"] is False


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(kind="research_release"),
    lambda d: d.update(scientific_result=True),
    lambda d: d["mri"]["points"][1].update(point_id="qA"),
    lambda d: d["mri"]["points"][1].update(descriptor_row=0),
    lambda d: d["mri"]["points"][1].update(descriptor_row=True),
    lambda d: d["mri"]["descriptors"][0].__setitem__(0, float("nan")),
    lambda d: d["mri"]["points"][0].update(i=float("inf")),
    lambda d: d["mri"]["descriptors"].__setitem__(0, [0, 0]),
    lambda d: d["candidates"]["keep_ids"].append("u17"),
    lambda d: d["candidates"]["keep_ids"].append("unknown"),
    lambda d: d["candidates"]["remove_ids"].append("u17"),
])
def test_invalid_interface_rejected(sample, mutation):
    mutation(sample)
    with pytest.raises(ValueError):
        validate_fixture(sample)


@pytest.mark.parametrize("function", [match, fit, evaluate, summarize, run_matrix])
def test_production_shell_fails_without_reading_or_writing(function, tmp_path):
    args = {name: tmp_path / name for name in inspect.signature(function).parameters}
    with pytest.raises(StageNotImplemented):
        function(**args)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command,fields", [
    ("fit", ["pairs", "mri-points", "us-points", "config", "output"]),
    ("evaluate", ["release", "predictions", "reference", "output"]),
    ("summarize", ["metrics", "query-evaluation", "output"]),
    ("run-matrix", ["release", "config", "output"]),
])
def test_cli_unimplemented_exit_and_no_outputs(command, fields, tmp_path, capsys):
    args = [command]
    for field in fields:
        args.extend(["--" + field, "MNN" if field == "method-id" else str(tmp_path / field)])
    assert main(args) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["status"] == "NOT_IMPLEMENTED"
    assert list(tmp_path.iterdir()) == []


def test_predictors_have_no_reference_argument(tmp_path):
    with pytest.raises(TypeError):
        match(reference=tmp_path)
    with pytest.raises(TypeError):
        fit(reference=tmp_path)
    assert "reference" not in inspect.signature(match).parameters
    assert "reference" not in inspect.signature(fit).parameters


def test_working_cli_status_and_fixture(capsys):
    assert main(["status"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state['scientific_run_history'] == 'NOT_INSPECTED' and state['execution_by_status'] is False
    assert main(["inspect-fixture", str(FIXTURE)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "STRUCTURE_VALID"
