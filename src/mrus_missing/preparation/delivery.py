"""Deterministic archives for separate input/reference handoff; no uploading."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .files import digest, require, validate_release_id, write_json
from .release import INPUT_FILES, REFERENCE_FILES, verify_inputs, verify_reference


def _archive(source: Path, names: set[str], target: Path) -> dict:
    with ZipFile(target, 'x', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (source / name).read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    return {'filename': target.name, 'sha256': digest(target.read_bytes()), 'size_bytes': target.stat().st_size}


def package_inputs(release: Path, reference: Path, output: Path, *, expected_kind='research_input') -> dict:
    """Package verified files into two archives; old answers stay out of inputs."""
    inp = verify_inputs(release, expected_kind=expected_kind)
    ref = verify_reference(reference, release, expected_kind=expected_kind)
    name = validate_release_id(inp.get('release_id'))
    output = output.resolve()
    require(not output.exists(), 'delivery output exists; never overwrite')
    require(not output.is_relative_to(release.resolve()) and not output.is_relative_to(reference.resolve()),
            'delivery must be outside immutable input folders')
    targets = [(output / (name + suffix)).resolve() for suffix in ('-inputs.zip', '-reference.zip')]
    require(all(target.parent == output for target in targets), 'archive path escapes delivery output')
    output.mkdir(parents=True, exist_ok=False)
    prediction = _archive(release, INPUT_FILES | {'manifest.json'}, targets[0])
    evaluation = _archive(reference, REFERENCE_FILES | {'reference_manifest.json'}, targets[1])
    result = {'schema_version': 'mrus-delivery/1', 'release_id': name, 'kind': expected_kind,
              'distribution': 'RESTRICTED_TEAM_HANDOFF', 'public_upload_authorized': False,
              'input_manifest_sha256': inp['manifest_sha256'],
              'reference_manifest_sha256': ref['reference_manifest_sha256'],
              'archives': {'inputs_for_B_C_D': prediction, 'reference_for_A_D': evaluation},
              'scientific_runs': 'NOT_RUN', 'D_review': 'PENDING'}
    write_json(output / 'delivery.json', result)
    return result
