"""Create and verify immutable input releases; never run B/C/D algorithms."""
import re
import shutil
from pathlib import Path

import numpy as np

from .files import (check_seal, digest, file_specs, read_csv, read_json, read_verified,
                    require, seal, write_csv, write_json)
from .legacy import audit_source

POINT_FIELDS = ["point_id", "descriptor_row", "i", "j", "k", "source_id"]
INPUT_FILES = {"mri_descriptors.npy", "us_descriptors.npy", "mri_points.csv", "us_points.csv",
               "conditions.json", "experiment.json", "attribution.json"}
REFERENCE_FILES = {"reference.json", "correspondences.csv", "baseline_pairs.csv",
                   "baseline_transform.json", "input_audit.json", "source_evidence.json"}
CONDITIONS = ["FULL", "RAND_1", "RAND_2", "RAND_3", "SPATIAL_I", "SPATIAL_J", "SPATIAL_K"]


def validate_config(config: dict) -> None:
    require(config["protocol_version"] == "1.0" and config["matrix_rows"] == 14
            and config["methods"] == ["MNN", "MNN_RATIO"], "unsupported experiment protocol")
    require([x["condition_id"] for x in config["conditions"]] == CONDITIONS, "condition order differs")
    require(config["matching"]["eps"] == 1e-12 and config["matching"]["ratio_threshold"] == 0.8
            and config["matching"]["distance"] == "L2"
            and config["matching"]["renormalize"] is False, "matching configuration differs")
    for i, c in enumerate(config["conditions"]):
        require(c["keep_count"] == (64 if i == 0 else 48)
                and c["remove_count"] == (0 if i == 0 else 16), "condition counts differ")
        if 1 <= i <= 3:
            require(c["seed"] == 2026101000 + i and c["rng"] == "PCG64"
                    and c["basis"] == "stable_id_ascending", "random protocol differs")
        if i >= 4:
            require(c["axis"] == "IJK"[i - 4]
                    and c["order"] == "coordinate_descending_then_id_ascending",
                    "spatial protocol differs")


def build_conditions(ids: list[str], points: np.ndarray, config: dict, input_sha: str) -> dict:
    """Choose candidate IDs once, then retain matching order from the source."""
    validate_config(config)
    require(len(ids) == len(set(ids)) == 64 and points.shape == (64, 3)
            and np.isfinite(points).all(), "invalid candidate basis")
    stable = sorted(ids)
    by_id = dict(zip(ids, points))
    result = []
    for spec in config["conditions"]:
        cid = spec["condition_id"]
        if cid == "FULL":
            chosen = []
        elif cid.startswith("RAND_"):
            indices = np.random.Generator(np.random.PCG64(spec["seed"])).choice(64, 16, replace=False)
            chosen = [stable[int(i)] for i in indices]
        else:
            axis = "IJK".index(spec["axis"])
            chosen = sorted(ids, key=lambda p: (-by_id[p][axis], p))[:16]
        removed = set(chosen)
        result.append({**spec, "selected_removal_order": chosen,
                       "keep_ids": [p for p in ids if p not in removed],
                       "remove_ids": [p for p in ids if p in removed]})
    return {"schema_version": "conditions-v1", "source_us_descriptors_sha256": input_sha,
            "numerical_order": "original_us_descriptor_row", "conditions": result}


def _manifest(root: Path, name: str, schema: str, files: set[str], expected_sha256=None, read_names=None) -> dict:
    path = root / name
    if expected_sha256:
        require(digest(path.read_bytes()) == expected_sha256, "external manifest SHA-256 mismatch")
    m = read_json(path)
    check_seal(m)
    require(m["schema_version"] == schema and set(m["files"]) == files,
            "release schema/file allowlist differs")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    require(actual == files | {name}, "unexpected or missing release files")
    for key, spec in m["files"].items():
        require(spec["path"] == key, "file path must equal manifest key")
        if read_names is None or key in read_names:
            read_verified(root, spec)
    return m


def _points(path: Path, count: int) -> tuple[list[str], np.ndarray]:
    rows = read_csv(path)
    require(len(rows) == count and all(set(r) == set(POINT_FIELDS) for r in rows), "points CSV schema/count")
    ids = [r["point_id"] for r in rows]
    require(all(ids) and len(set(ids)) == count, "duplicate/empty point IDs")
    require(all(re.fullmatch(r"0|[1-9][0-9]*", r["descriptor_row"]) for r in rows), "invalid descriptor row")
    require(sorted(int(r["descriptor_row"]) for r in rows) == list(range(count)), "descriptor row coverage")
    ordered = sorted(rows, key=lambda r: int(r["descriptor_row"]))
    require(all(r["source_id"] == r["point_id"] for r in ordered), "source ID binding differs")
    xyz = np.array([[float(r[k]) for k in ("i", "j", "k")] for r in ordered], dtype=np.float64)
    require(bool(np.isfinite(xyz).all()), "nonfinite coordinate")
    return [r["point_id"] for r in ordered], xyz


def _read_inputs(release: Path, expected_kind="research_input", expected_sha256=None) -> dict:
    m = _manifest(release, "manifest.json", "mrus-input-release/1", INPUT_FILES, expected_sha256)
    require(m["kind"] == expected_kind, "input kind mismatch; synthetic is not research")
    require(m["scientific_runs"] == "NOT_RUN" and m["shape"] == [64, 512]
            and m["model"]["producer_type"] == "MODEL_TRAINED", "input/model contract differs")
    require(m["unit"] == "index_unit" and m["coordinate_order"] == ["I", "J", "K"], "coordinate contract differs")
    arrays, ids, points = {}, {}, {}
    for side in ("mri", "us"):
        array = np.load(release / f"{side}_descriptors.npy", allow_pickle=False)
        require(array.dtype == np.float32 and array.shape == (64, 512)
                and np.isfinite(array).all()
                and (np.linalg.norm(array.astype(np.float64), axis=1) > 1e-12).all(), "invalid descriptors")
        arrays[side] = array
        ids[side], points[side] = _points(release / f"{side}_points.csv", 64)
        require(ids[side] == m["descriptor_ids"][side], "descriptor ID binding differs")
    config = read_json(release / "experiment.json")
    require(digest((release / "experiment.json").read_bytes()) == m["experiment_sha256"], "experiment binding differs")
    expected = build_conditions(ids["us"], points["us"], config, m["files"]["us_descriptors.npy"]["sha256"])
    require(read_json(release / "conditions.json") == expected, "candidate lists/rules/order differ")
    return {"manifest": m, "arrays": arrays, "ids": ids, "points": points, "conditions": expected}


def verify_inputs(release: Path, expected_sha256=None, *, expected_kind="research_input") -> dict:
    """Verify integrity/identity and seven candidate lists, without predictions."""
    data = _read_inputs(release, expected_kind, expected_sha256)
    return {"status": "INPUT_RELEASE_VALID", "kind": data["manifest"]["kind"],
            "release_id": data["manifest"]["release_id"],
            "manifest_sha256": digest((release / "manifest.json").read_bytes()),
            "descriptor_shape": [64, 512], "conditions": 7, "planned_matrix_rows": 14,
            "scientific_runs": "NOT_RUN", "D_review": "PENDING"}


def load_matching_inputs(release: Path, condition_id: str, expected_sha256=None, *, expected_kind='research_input') -> dict:
    """Return descriptor-only B inputs; no coordinates/reference/old pairs returned."""
    names = {"mri_descriptors.npy", "us_descriptors.npy", "conditions.json", "experiment.json"}
    m = _manifest(release, "manifest.json", "mrus-input-release/1", INPUT_FILES,
                  expected_sha256, read_names=names)
    require(m['kind'] == expected_kind and m['model']['producer_type'] == 'MODEL_TRAINED', 'input kind/model mismatch')
    ids = m['descriptor_ids']
    arrays = {}
    for side in ('mri', 'us'):
        require(len(ids[side]) == len(set(ids[side])) == 64, 'descriptor IDs invalid')
        arrays[side] = np.load(release / f'{side}_descriptors.npy', allow_pickle=False)
        require(arrays[side].dtype == np.float32 and arrays[side].shape == (64, 512)
                and np.isfinite(arrays[side]).all()
                and (np.linalg.norm(arrays[side].astype(np.float64), axis=1) > 1e-12).all(), 'invalid descriptor array')
    conditions = read_json(release / 'conditions.json')
    condition = next((c for c in conditions['conditions'] if c['condition_id'] == condition_id), None)
    require(condition is not None, "unknown condition")
    keep, remove = condition['keep_ids'], condition['remove_ids']
    require(len(keep) == len(set(keep)) == (64 if condition_id == 'FULL' else 48)
            and len(remove) == len(set(remove)) == (0 if condition_id == 'FULL' else 16)
            and not set(keep) & set(remove) and set(keep) | set(remove) == set(ids['us']), 'invalid candidate partition')
    require(keep == [p for p in ids['us'] if p in keep], 'candidate source order differs')
    by_id = {p: i for i, p in enumerate(ids['us'])}
    columns = [by_id[p] for p in condition["keep_ids"]]
    return {"mri_descriptors": arrays['mri'], "us_descriptors": arrays['us'][columns],
            "query_ids": ids['mri'], "candidate_ids": keep,
            "candidate_source_rows": columns, "release_id": m['release_id']}


def load_geometry_points(release: Path, expected_sha256=None, *, expected_kind='research_input') -> dict:
    """Return C's ID-to-coordinate tables; no reference or fit is produced."""
    data = _read_inputs(release, expected_kind=expected_kind, expected_sha256=expected_sha256)
    return {side: dict(zip(data["ids"][side], data["points"][side])) for side in ("mri", "us")}


def verify_reference(reference: Path, release: Path, expected_sha256=None, *, expected_kind="research_input") -> dict:
    """Validate the separate old-evidence package and its exact input binding."""
    data = _read_inputs(release, expected_kind)
    m = _manifest(reference, "reference_manifest.json", "mrus-evaluation-reference/1", REFERENCE_FILES, expected_sha256)
    require(m["kind"] == expected_kind and m["release_id"] == data["manifest"]["release_id"], "reference identity mismatch")
    require(m["input_manifest_sha256"] == digest((release / "manifest.json").read_bytes()), "mixed reference/input release")
    ref = read_json(reference / "reference.json")
    require(ref["direction"] == "US_TO_MR" and ref["unit"] == "index_unit", "reference direction/unit differs")
    require(np.array_equal(ref["R"], np.eye(3)) and ref["t"] == [-4., 3., -2.]
            and ref["correctness_threshold"] == 0.5, "reference protocol differs")
    probes = np.asarray(ref["probes_us"], dtype=np.float64)
    require(probes.shape == (8, 3) and np.isfinite(probes).all(), "reference probe contract")
    corr = read_csv(reference / "correspondences.csv")
    require(len(corr) == 64 and len({p['query_id'] for p in corr}) == 64
            and len({p['candidate_id'] for p in corr}) == 64, "reference pairs not one-to-one")
    q = dict(zip(data["ids"]["mri"], data["points"]["mri"]))
    u = dict(zip(data["ids"]["us"], data["points"]["us"]))
    require(set(q) == {p['query_id'] for p in corr} and set(u) == {p['candidate_id'] for p in corr}, "reference ID coverage")
    require(all(np.linalg.norm(u[p['candidate_id']] + ref['t'] - q[p['query_id']]) <= 0.5 for p in corr), "reference coordinate mismatch")
    pairs = read_csv(reference / "baseline_pairs.csv")
    mapping = {p['query_id']: p['candidate_id'] for p in corr}
    require(len(pairs) == 47 and len({p['query_id'] for p in pairs}) == 47
            and all(mapping.get(p['query_id']) == p['candidate_id'] for p in pairs), "historical baseline differs")
    audit = read_json(reference / "input_audit.json")
    require(audit["new_matching_run"] == audit["matrix"] == "NOT_RUN", "historical evidence mislabeled")
    return {"status": "REFERENCE_PACKAGE_VALID", "release_id": m["release_id"],
            "reference_manifest_sha256": digest((reference / "reference_manifest.json").read_bytes()),
            "historical_pairs": 47, "original_probes": 8, "scientific_runs": "NOT_RUN", "D_review": "PENDING"}


def prepare(source: Path, config: Path, output: Path, reference_output: Path) -> dict:
    """Audit locked legacy source and create two new, separate immutable folders."""
    config = config.resolve()
    cfg = read_json(config)
    validate_config(cfg)
    lock = read_json(config.parent / "source-crosskey-v1.json")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", lock['release_id']) is not None, "invalid release ID")
    source, output, reference_output = source.resolve(), output.resolve(), reference_output.resolve()
    require(not output.exists() and not reference_output.exists(), "output already exists; never overwrite a release")
    require(not output.is_relative_to(source) and not reference_output.is_relative_to(source), "output must not alter source tree")
    require(not output.is_relative_to(reference_output) and not reference_output.is_relative_to(output), "input/reference roots must be separate")
    audited = audit_source(source, lock)
    output.mkdir(parents=True, exist_ok=False)
    reference_output.mkdir(parents=True, exist_ok=False)
    for side in ("mri", "us"):
        (output / f"{side}_descriptors.npy").write_bytes(audited["vector_bytes"][side])
        rows = [{"point_id": pid, "descriptor_row": row, "i": xyz[0], "j": xyz[1], "k": xyz[2], "source_id": pid}
                for row, (pid, xyz) in enumerate(zip(audited["ids"][side], audited["points"][side]))]
        write_csv(output / f"{side}_points.csv", rows, POINT_FIELDS)
    shutil.copyfile(config, output / "experiment.json")
    write_json(output / "conditions.json", build_conditions(audited['ids']['us'], audited['points']['us'], cfg, digest(audited['vector_bytes']['us'])))
    write_json(output / "attribution.json", lock['attribution'])
    model = {key: lock[key] for key in ('encoder_id', 'checkpoint_sha256', 'preprocess_id')}
    write_json(output / "manifest.json", seal({
        "schema_version": "mrus-input-release/1", "kind": lock['kind'], "release_id": lock['release_id'],
        "scientific_runs": "NOT_RUN", "status": "READY_FOR_MODULE_DEVELOPMENT",
        "D_review": "PENDING", "shape": [64, 512], "model": {**model, "producer_type": "MODEL_TRAINED"},
        "unit": "index_unit", "coordinate_order": ['I', 'J', 'K'], "descriptor_ids": audited['ids'],
        "source_snapshot_commit": lock['source_snapshot_commit'],
        "source_lock_sha256": digest((config.parent / 'source-crosskey-v1.json').read_bytes()),
        "preparation_source_hashes": {p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*.py'))},
        "experiment_sha256": digest((output / 'experiment.json').read_bytes()),
        "sources": {k: v for k, v in audited['sources'].items() if k in ('mri_descriptors', 'us_descriptors', 'mri_points', 'us_points')},
        "files": file_specs(output, sorted(INPUT_FILES))}))
    original = audited['reference']
    write_json(reference_output / "reference.json", {"direction": "US_TO_MR", "unit": "index_unit",
        "R": original['R'], "t": original['t'], "probes_us": original['probes_us'],
        "source_frame_id": original['source_frame_id'], "target_frame_id": original['target_frame_id'],
        "correctness_threshold": original['correctness_threshold'], "probes_source": "original_reference_payload",
        "visibility": "evaluation_only"})
    write_csv(reference_output / "correspondences.csv", audited['correspondences'], ['query_id', 'candidate_id'])
    rows = [{"query_id": p['mr_id'], "candidate_id": p['us_id'], "d1": p['distance'], "d2": p['second_distance'], "ratio": p['ratio']} for p in audited['pairs']]
    write_csv(reference_output / "baseline_pairs.csv", rows, ['query_id', 'candidate_id', 'd1', 'd2', 'ratio'])
    write_json(reference_output / "baseline_transform.json", {"kind": "historical_output", **audited['transform']})
    write_json(reference_output / "input_audit.json", audited['audit'])
    write_json(reference_output / "source_evidence.json", {"sources": audited['sources'],
        "source_snapshot_commit": lock['source_snapshot_commit'],
        "scope": "Only listed small payloads verified; volumes, images and weights not read."})
    write_json(reference_output / "reference_manifest.json", seal({
        "schema_version": "mrus-evaluation-reference/1", "kind": lock['kind'], "release_id": lock['release_id'],
        "input_manifest_sha256": digest((output / 'manifest.json').read_bytes()),
        "files": file_specs(reference_output, sorted(REFERENCE_FILES))}))
    again = audit_source(source, lock)
    require(again['sources'] == audited['sources'], "source changed during preparation")
    return {"status": "PREPARED", "input": verify_inputs(output, expected_kind=lock['kind']),
            "reference": verify_reference(reference_output, output, expected_kind=lock['kind']),
            "audit": audited['audit'], "source_unchanged": True}
