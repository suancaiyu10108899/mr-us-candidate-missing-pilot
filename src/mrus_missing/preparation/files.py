"""Bounded files, hashes and stable serialization for A's input contracts."""
import csv
import hashlib
import io
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_release_id(value: object) -> str:
    """Use one bounded filename-component rule at creation and consumption."""
    require(isinstance(value, str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value) is not None,
            "invalid release ID")
    return value


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode_json(blob: bytes) -> dict:
    """Decode already verified bytes without reopening a mutable path."""
    require(len(blob) <= 1024 * 1024, "JSON exceeds 1 MiB")
    def invalid_constant(value):
        raise ValueError("nonfinite JSON value")
    result = json.loads(blob, object_pairs_hook=_unique_object,
                        parse_constant=invalid_constant)
    require(isinstance(result, dict), "JSON object required")
    return result


def read_json(path: Path) -> dict:
    require(path.stat().st_size <= 1024 * 1024, "JSON exceeds 1 MiB")
    return decode_json(path.read_bytes())


def inside(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), "relative path required")
    p = PurePosixPath(relative)
    require(not p.is_absolute() and "\\" not in relative and ":" not in relative
            and all(part not in ("", ".", "..") for part in relative.split("/")),
            "unsafe relative path")
    result = root.joinpath(*p.parts).resolve()
    require(result.is_relative_to(root.resolve()), "path escapes input root")
    return result


def read_verified(root: Path, spec: dict) -> bytes:
    path = inside(root, spec["path"])
    require(path.is_file(), "required payload missing")
    require(path.stat().st_size == spec["size_bytes"] <= 1024 * 1024,
            "payload size mismatch or exceeds 1 MiB")
    blob = path.read_bytes()
    require(digest(blob) == spec["sha256"], "payload SHA-256 mismatch")
    return blob


def seal(data: dict) -> dict:
    require("content_sha256" not in data, "cannot reseal existing manifest")
    return {**data, "content_sha256": digest(canonical(data))}


def check_seal(data: dict) -> None:
    expected = data.get("content_sha256")
    core = {k: v for k, v in data.items() if k != "content_sha256"}
    require(expected == digest(canonical(core)), "manifest content SHA-256 mismatch")


def write_json(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2,
                                allow_nan=False) + "\n")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    require(path.stat().st_size <= 1024 * 1024, "CSV exceeds 1 MiB")
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def file_specs(root: Path, names: list[str]) -> dict:
    return {name: {"path": name, "sha256": digest((root / name).read_bytes()),
                   "size_bytes": (root / name).stat().st_size} for name in names}
