"""Input utilities and A orchestration; runtime capabilities are branch-specific."""

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from mrus_missing.contracts import inspect_fixture
from mrus_missing.errors import StageNotImplemented
from mrus_missing.evaluation import evaluate, summarize
from mrus_missing.geometry import fit
from mrus_missing.matching_runner import match_fixture, match_release, matching_capabilities
from mrus_missing.preparation import prepare, verify_inputs, verify_reference
from mrus_missing.preparation.delivery import package_inputs


def run_matrix(release: Path, config: Path, output: Path) -> None:
    """Reserve A's future orchestration without fabricating downstream output."""
    raise StageNotImplemented("run-matrix", "A")


def build_parser() -> argparse.ArgumentParser:
    """Expose future inputs without implementing scientific stages."""
    parser = argparse.ArgumentParser(description="Pilot input tools and debug matching; no matrix execution")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show APIs available in this checkout; not a run-history audit")
    fixture = sub.add_parser("inspect-fixture", help="validate synthetic interface only")
    fixture.add_argument("path", type=Path)
    specs = {
        "prepare": (prepare, ("source", "config", "output", "reference_output")),
        "verify-inputs": (verify_inputs, ("release",)),
        "verify-reference": (verify_reference, ("reference", "release")),
        "package-inputs": (package_inputs, ("release", "reference", "output")),
        "match": (match_release, ("release", "condition_id", "method_id", "expected_sha256", "output", "run_id", "operator")),
        "match-fixture": (match_fixture, ("fixture", "config", "method_id", "output", "run_id", "operator")),
        "fit": (fit, ("pairs", "mri_points", "us_points", "config", "output")),
        "evaluate": (evaluate, ("release", "predictions", "reference", "output")),
        "summarize": (summarize, ("metrics", "query_evaluation", "output")),
        "run-matrix": (run_matrix, ("release", "config", "output")),
    }
    for name, (handler, fields) in specs.items():
        implemented = name in ('prepare', 'verify-inputs', 'verify-reference', 'package-inputs', 'match', 'match-fixture')
        stage = sub.add_parser(name, help="A input/matching integration; matching needs B API" if implemented else "NOT_IMPLEMENTED production interface")
        for field in fields:
            options = {"required": True, "type": str if field.endswith("_id") or field in ('expected_sha256', 'operator') else Path}
            if field == "method_id":
                options["choices"] = ("MNN", "MNN_RATIO")
            stage.add_argument("--" + field.replace("_", "-"), **options)
        if name in ('verify-inputs', 'verify-reference'):
            stage.add_argument('--expected-sha256', help='trusted manifest file SHA-256 from the handoff')
            fields = (*fields, 'expected_sha256')
        if name == 'match':
            stage.add_argument('--input-kind', choices=('research_input', 'synthetic_fixture'), default='research_input')
            fields = (*fields, 'input_kind')
        stage.set_defaults(handler=handler, fields=fields)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 for structural checks, 2 for invalid input, 3 for absent stages."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            result = {'project_state': 'A_INPUT_AND_MATCHING_INTEGRATION',
                      'matching_apis_in_this_checkout': matching_capabilities(),
                      'fit_evaluate_matrix': 'NOT_IMPLEMENTED', 'matrix_rows_planned': 14,
                      'scientific_run_history': 'NOT_INSPECTED', 'execution_by_status': False}
        elif args.command == "inspect-fixture":
            result = inspect_fixture(args.path)
        else:
            result = args.handler(**{name: getattr(args, name) for name in args.fields})
            if result is None:
                raise RuntimeError("stage returned without a defined result contract")
    except StageNotImplemented as error:
        print(json.dumps({"status": "NOT_IMPLEMENTED", "stage": error.stage,
                          "owner": error.owner, "scientific_runs": "NOT_RUN"}), file=sys.stderr)
        return 3
    except (OSError, ValueError, KeyError, TypeError) as error:
        reason = "cannot read or create requested files" if isinstance(error, OSError) else str(error)
        print(json.dumps({"status": "INVALID_INPUT", "reason": reason}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
