"""Public status/help must stay truthful as C and D arrive independently."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mrus_missing import capabilities, cli


@pytest.mark.parametrize("c_ready,d_ready", [(False, False), (True, False), (False, True), (True, True)])
def test_status_and_help_follow_independent_backends(c_ready, d_ready, monkeypatch, capsys):
    def never_execute(*args, **kwargs):
        raise AssertionError("status/help must not execute a backend")

    geometry = SimpleNamespace(fit=never_execute)
    evaluation = SimpleNamespace(evaluate=never_execute, summarize=never_execute)
    if c_ready:
        geometry.fit_arrays = geometry.estimate = never_execute
    if d_ready:
        evaluation.classify_query = evaluation.metrics_from_counts = never_execute
    modules = {"mrus_missing.geometry": geometry, "mrus_missing.evaluation": evaluation}
    monkeypatch.setattr(capabilities.importlib, "import_module", modules.__getitem__)
    missing_b = lambda: {"match": False, "match_fixture": False, "algorithm_acceptance": "NOT_ASSESSED"}
    monkeypatch.setattr(capabilities, "matching_capabilities", missing_b)
    monkeypatch.setattr(cli, "matching_capabilities", missing_b)
    monkeypatch.setattr(Path, "open", never_execute)
    assert cli.main(["status"]) == 0
    status = json.loads(capsys.readouterr().out)
    states = status["stage_apis_in_this_checkout"]
    assert states["fit"] is c_ready
    assert states["evaluate"] is states["summarize"] is d_ready
    assert states["run_matrix"] is False
    assert status["algorithm_acceptance"] == "NOT_ASSESSED"
    assert status["scientific_run_history"] == "NOT_INSPECTED"
    assert status["execution_by_status"] is False
    for command, ready in (("fit", c_ready), ("evaluate", d_ready),
                           ("summarize", d_ready), ("run-matrix", False)):
        with pytest.raises(SystemExit) as stopped:
            cli.main([command, "--help"])
        assert stopped.value.code == 0
        assert ("NOT_IMPLEMENTED" in capsys.readouterr().out) is not ready


@pytest.mark.parametrize("broken_api", ["fit_arrays", "estimate"])
def test_partial_geometry_api_is_not_advertised(broken_api, monkeypatch):
    function = lambda: None
    geometry = SimpleNamespace(fit=function, fit_arrays=function, estimate=function)
    setattr(geometry, broken_api, None)
    modules = {"mrus_missing.geometry": geometry, "mrus_missing.evaluation": SimpleNamespace()}
    monkeypatch.setattr(capabilities.importlib, "import_module", modules.__getitem__)
    monkeypatch.setattr(capabilities, "matching_capabilities", lambda: {"match": False, "match_fixture": False})
    assert capabilities.stage_capabilities()["fit"] is False
