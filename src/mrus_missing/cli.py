"""Honest CLI shell: structural fixture checks work; scientific stages fail."""

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from mrus_missing.contracts import inspect_fixture
from mrus_missing.errors import StageNotImplemented
from mrus_missing.evaluation import evaluate, summarize
from mrus_missing.geometry import fit
from mrus_missing.matching import match
from mrus_missing.preparation import prepare


def run_matrix(release: Path, config: Path, output: Path) -> None:
    """Reserve A's future orchestration without fabricating downstream output."""
    raise StageNotImplemented("run-matrix", "A")


def build_parser() -> argparse.ArgumentParser:
    """Expose future inputs without implementing scientific stages."""
    parser = argparse.ArgumentParser(description="Bootstrap only; research NOT_RUN")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show truthful bootstrap state")
    fixture = sub.add_parser("inspect-fixture", help="validate synthetic interface only")
    fixture.add_argument("path", type=Path)
    specs = {
        "prepare": (prepare, ("source", "config", "output")),
        "match": (match, ("mri_descriptors", "us_descriptors", "conditions", "condition_id", "method_id", "output")),
        "fit": (fit, ("pairs", "mri_points", "us_points", "config", "output")),
        "evaluate": (evaluate, ("release", "predictions", "reference", "output")),
        "summarize": (summarize, ("metrics", "query_evaluation", "output")),
        "run-matrix": (run_matrix, ("release", "config", "output")),
    }
    for name, (handler, fields) in specs.items():
        stage = sub.add_parser(name, help="NOT_IMPLEMENTED production interface")
        for field in fields:
            options = {"required": True, "type": str if field.endswith("_id") else Path}
            if field == "method_id":
                options["choices"] = ("MNN", "MNN_RATIO")
            stage.add_argument("--" + field.replace("_", "-"), **options)
        stage.set_defaults(handler=handler, fields=fields)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 for structural checks, 2 for invalid input, 3 for absent stages."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            result = {"project_state": "BOOTSTRAP", "scientific_runs": "NOT_RUN",
                      "core_algorithms": "NOT_IMPLEMENTED", "matrix_rows_planned": 14}
        elif args.command == "inspect-fixture":
            result = inspect_fixture(args.path)
        else:
            args.handler(**{name: getattr(args, name) for name in args.fields})
            raise RuntimeError("stage returned without a defined result contract")
    except StageNotImplemented as error:
        print(json.dumps({"status": "NOT_IMPLEMENTED", "stage": error.stage,
                          "owner": error.owner, "scientific_runs": "NOT_RUN"}), file=sys.stderr)
        return 3
    except (OSError, ValueError) as error:
        reason = "cannot read fixture" if isinstance(error, OSError) else str(error)
        print(json.dumps({"status": "INVALID_INPUT", "reason": reason}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
