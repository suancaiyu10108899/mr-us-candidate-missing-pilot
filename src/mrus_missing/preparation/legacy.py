"""Read a locked subset of legacy artifacts. No legacy algorithm is imported."""
import io
import json
from pathlib import Path

import numpy as np

from .files import check_seal, digest, inside, read_json, read_verified, require


def _array(blob: bytes, dtype: str, shape: tuple) -> np.ndarray:
    value = np.load(io.BytesIO(blob), allow_pickle=False)
    require(isinstance(value, np.ndarray) and value.dtype == np.dtype(dtype)
            and value.shape == shape, "array dtype/shape mismatch")
    require(bool(np.isfinite(value).all()), "nonfinite array")
    return value


def _ids(values: list, count: int) -> None:
    require(isinstance(values, list) and len(values) == count
            and all(isinstance(x, str) and bool(x) for x in values)
            and len(set(values)) == count, "invalid or duplicate point IDs")


def audit_source(source: Path, lock: dict) -> dict:
    """Verify existing input identities and old evidence, without new predictions.

    Only two vector arrays, two coordinate arrays, old pairs and one reference
    JSON are read. Volume arrays, images, patches and model weights are untouched.
    The returned producer audit does not replace D's independent evaluation.
    """
    require(lock.get("schema_version") == "source-lock-v1", "source lock schema")
    require(lock.get("kind") in ("research_input", "synthetic_fixture"), "source kind")
    n, dimension = lock["shape"]
    require((n, dimension) == (64, 512), "pilot requires 64 x 512 descriptors")
    manifests, roots, evidence = {}, {}, {}
    for name, spec in lock["artifacts"].items():
        root = inside(source, spec["path"])
        path = inside(root, "manifest.json")
        blob = path.read_bytes()
        require(digest(blob) == spec["manifest_sha256"], "source manifest file SHA mismatch")
        manifest = read_json(path)
        check_seal(manifest)
        require(manifest["schema_version"] == "pilot-v1", "legacy schema mismatch")
        for field in ("artifact_id", "content_sha256", "artifact_type"):
            require(manifest[field] == spec[field], "locked artifact identity mismatch")
        manifests[name], roots[name] = manifest, root
        evidence[name] = {k: spec[k] for k in
                          ("artifact_id", "content_sha256", "manifest_sha256", "artifact_type")}
        evidence[name]["payloads_verified"] = {}

    def payload(name, key):
        spec = manifests[name]["payloads"][key]
        value = read_verified(roots[name], spec)
        evidence[name]["payloads_verified"][key] = dict(spec)
        return value

    def identity(name):
        m = manifests[name]
        return {k: m[k] for k in ("artifact_id", "content_sha256")}

    vectors, points, ids, vector_bytes = {}, {}, {}, {}
    for side, modality in (("mri", "MRI"), ("us", "US")):
        dname, pname = side + "_descriptors", side + "_points"
        descriptor, pointset = manifests[dname], manifests[pname]
        d, p = descriptor["meta"], pointset["meta"]
        _ids(d["point_ids"], n)
        _ids(p["point_ids"], n)
        require(set(d["point_ids"]) == set(p["point_ids"]), "descriptor/point IDs differ")
        require(d["producer_type"] == "MODEL_TRAINED" and d["modality"] == modality,
                "trained model or modality mismatch")
        for field in ("checkpoint_sha256", "encoder_id", "preprocess_id"):
            require(d[field] == lock[field], "model/preprocess identity mismatch")
        require(descriptor["code_commit"] == lock["scientific_source_commit"],
                "descriptor source commit mismatch")
        require(d["pointset"] == identity(pname) and identity(pname) in descriptor["parents"],
                "descriptor PointSet parent mismatch")
        require(d["frame_id"] == p["frame_id"] and p["unit"] == "index_unit"
                and p["coordinate_order"] == ["I", "J", "K"], "point frame/unit/order mismatch")
        raw = payload(dname, d["vectors_payload"])
        vector_bytes[side] = raw
        vectors[side] = _array(raw, "float32", (n, dimension))
        require(bool((np.linalg.norm(vectors[side].astype(np.float64), axis=1) > 1e-12).all()),
                "zero descriptor")
        coords = _array(payload(pname, p["coordinates_payload"]), "float64", (n, 3))
        by_id = dict(zip(p["point_ids"], coords))
        ids[side] = d["point_ids"]
        points[side] = np.array([by_id[x] for x in ids[side]], dtype=np.float64)

    refmeta = manifests["reference"]["meta"]
    reference = json.loads(payload("reference", refmeta["evaluation_reference_payload"]))
    require(reference["visibility"] == "eval-only" and reference["unit"] == "index_unit",
            "reference visibility/unit mismatch")
    require(reference["source_frame_id"] == manifests["us_points"]["meta"]["frame_id"]
            and reference["target_frame_id"] == manifests["mri_points"]["meta"]["frame_id"],
            "reference frame mismatch")
    require(reference["pointset_ids"]["MRI"] == manifests["mri_points"]["artifact_id"]
            and reference["pointset_ids"]["U_SHIFT"] == manifests["us_points"]["artifact_id"],
            "reference pointsets mismatch")
    R, t = np.asarray(reference["R"], dtype=np.float64), np.asarray(reference["t"], dtype=np.float64)
    require(R.shape == (3, 3) and t.shape == (3,) and np.array_equal(R, np.eye(3))
            and np.array_equal(t, [-4., 3., -2.]) and reference["correctness_threshold"] == 0.5,
            "reference differs from approved protocol")
    errors = np.linalg.norm(points["mri"][:, None] - (points["us"] @ R.T + t)[None, :], axis=2)
    correct = errors <= 0.5
    require(bool((correct.sum(axis=0) == 1).all() and (correct.sum(axis=1) == 1).all()),
            "reference is not unique one-to-one")
    _ids(reference["mr_ids"], n)
    _ids(reference["us_ids"], n)
    require(set(reference["mr_ids"]) == set(ids["mri"])
            and set(reference["us_ids"]) == set(ids["us"]), "reference IDs differ")
    correspondences = [{"query_id": q, "candidate_id": ids["us"][int(correct[i].argmax())]}
                       for i, q in enumerate(ids["mri"])]
    require(dict(zip(reference["mr_ids"], reference["us_ids"])) ==
            {p["query_id"]: p["candidate_id"] for p in correspondences},
            "reference list and coordinate relationship disagree")
    probes = np.asarray(reference["probes_us"], dtype=np.float64)
    probes_mr = np.asarray(reference["probes_mr"], dtype=np.float64)
    require(probes.shape == probes_mr.shape == (8, 3) and np.isfinite(probes).all()
            and np.isfinite(probes_mr).all() and np.allclose(probes @ R.T + t, probes_mr,
                                                            atol=1e-12, rtol=0),
            "original probes invalid or frames disagree")

    match = manifests["baseline_pairs"]
    require(all(identity(x) in match["parents"] for x in ("mri_descriptors", "us_descriptors")),
            "old matches descriptor parents mismatch")
    require(match["meta"]["mr_pointset"] == identity("mri_points")
            and match["meta"]["us_pointset"] == identity("us_points"), "old matches points mismatch")
    require(match["meta"]["distance_metric"] == "L2" and match["meta"]["ratio_threshold"] == 0.8
            and match["meta"]["mutual"] is True and match["meta"]["status"] == "SUCCESS",
            "old match configuration mismatch")
    pairs = json.loads(payload("baseline_pairs", match["meta"]["pairs_payload"]))
    require(len(pairs) == match["meta"]["accepted_count"] == 47, "historical pair count differs")
    require(len({p["mr_id"] for p in pairs}) == len({p["us_id"] for p in pairs}) == 47,
            "old pairs contain duplicate IDs")
    qrow, urow = ({p: i for i, p in enumerate(ids[s])} for s in ("mri", "us"))
    ordered = []
    max_distance_delta = 0.0
    # Audit only already accepted historical pairs. No predictions for the other 17 queries.
    for pair in pairs:
        require(pair["mr_id"] in qrow and pair["us_id"] in urow, "old pair ID absent")
        qi, ui = qrow[pair["mr_id"]], urow[pair["us_id"]]
        require(bool(correct[qi, ui]), "historical accepted pair is not reference-correct")
        distances = np.linalg.norm(vectors["us"].astype(np.float64) - vectors["mri"][qi].astype(np.float64), axis=1)
        d1, d2 = float(distances[ui]), float(np.min(np.delete(distances, ui)))
        reverse = np.linalg.norm(vectors["mri"].astype(np.float64) - vectors["us"][ui].astype(np.float64), axis=1)
        require(d2 - d1 > 1e-12 and np.min(np.delete(reverse, qi)) - reverse[qi] > 1e-12
                and d2 > 1e-12 and d1 / d2 < 0.8, "historical accepted pair fails stored rule")
        for actual, recorded in ((d1, pair["distance"]), (d2, pair["second_distance"]),
                                 (d1 / d2, pair["ratio"])):
            require(np.isclose(actual, recorded, atol=1e-10, rtol=1e-8), "old distance/ratio mismatch")
            max_distance_delta = max(max_distance_delta, abs(actual - recorded))
        ordered.append(qi)
    require(ordered == sorted(ordered), "old pairs not in query source order")

    transform = manifests["baseline_transform"]
    require(all(identity(x) in transform["parents"] for x in ("baseline_pairs", "mri_points", "us_points")),
            "old transform parent mismatch")
    tm = transform["meta"]
    require(tm["status"] == "SUCCESS" and tm["direction"] == "US_TO_MR"
            and tm["unit"] == "index_unit", "old transform state/direction mismatch")
    old_R, old_t = np.asarray(tm["R"], dtype=np.float64), np.asarray(tm["t"], dtype=np.float64)
    require(old_R.shape == (3, 3) and old_t.shape == (3,) and np.isfinite(old_R).all()
            and np.isfinite(old_t).all() and np.max(np.abs(old_R.T @ old_R - np.eye(3))) <= 1e-6
            and abs(np.linalg.det(old_R) - 1) <= 1e-6, "old transform invalid")
    old_probe_errors = np.linalg.norm(probes @ old_R.T + old_t - (probes @ R.T + t), axis=1)
    require(float(old_probe_errors.max()) <= 1e-5, "historical transform/reference discrepancy")
    return {"vectors": vectors, "vector_bytes": vector_bytes, "points": points, "ids": ids,
            "reference": reference, "correspondences": correspondences, "pairs": pairs,
            "transform": tm, "sources": evidence,
            "audit": {"scope": "A_producer_input_and_historical_artifact_audit",
                      "new_matching_run": "NOT_RUN", "matrix": "NOT_RUN", "D_review": "PENDING",
                      "unique_correspondences": n, "historical_pairs_checked": len(pairs),
                      "historical_pair_max_numeric_delta": max_distance_delta,
                      "original_probes_checked": len(probes),
                      "historical_transform_reference_probe_max": float(old_probe_errors.max()),
                      "images_weights_or_legacy_algorithms_loaded": False}}
