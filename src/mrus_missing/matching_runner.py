"""A-owned matching orchestration. Algorithms and file writer remain B-owned."""
import copy
from datetime import datetime, timezone
import importlib
import inspect
import json
from pathlib import Path
import platform
import re
import subprocess

import numpy as np

from .contracts import validate_fixture
from .errors import BackendContractError, StageNotImplemented
from .preparation import load_matching_request
from .preparation.files import canonical, decode_json, digest, read_json, require
from .preparation.release import validate_config


def matching_capabilities() -> dict:
    """Report APIs in this checkout, not another branch or scientific readiness."""
    backend = importlib.import_module('mrus_missing.matching')
    writer = callable(getattr(backend, 'write_match_outputs', None))
    return {'match': writer and callable(getattr(backend, 'match_inputs', None)),
            'match_fixture': writer and callable(getattr(backend, 'match_descriptors', None)),
            'algorithm_acceptance': 'NOT_ASSESSED'}


def _backend(api: str):
    backend = importlib.import_module('mrus_missing.matching')
    if not all(callable(getattr(backend, n, None)) for n in (api, 'write_match_outputs')):
        raise StageNotImplemented('B_matching_backend_in_current_checkout', 'B')
    return backend


def _code_identity(backend) -> dict:
    """Record actual editable checkout identity, including dirty-code fingerprints."""
    here = Path(__file__).resolve()
    def git(*args):
        p = subprocess.run(['git', '-C', str(here.parent), *args], capture_output=True, text=True)
        require(p.returncode == 0, 'matching requires an editable Git checkout')
        return p.stdout.strip()
    root = Path(git('rev-parse', '--show-toplevel')).resolve()
    require(here == root / 'src/mrus_missing/matching_runner.py',
            'use pip install -e . in the source checkout before matching')
    files = [here, root / 'src/mrus_missing/preparation/release.py',
             root / 'src/mrus_missing/preparation/files.py']
    for name in ('match_inputs', 'match_descriptors', 'write_match_outputs'):
        function = getattr(backend, name, None)
        if callable(function):
            path = Path(inspect.getsourcefile(function)).resolve()
            require(path.is_relative_to(root / 'src/mrus_missing/matching'), 'backend must belong to this checkout')
            files.append(path)
    return {'source_commit': git('rev-parse', 'HEAD'),
            'source_dirty': bool(git('status', '--porcelain', '--untracked-files=all')),
            'files_sha256': {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sorted(set(files))}}


def _preflight(output: Path, run_id: str, operator: str, protected: list[Path]) -> None:
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', run_id) is not None, 'invalid run_id')
    require(bool(operator.strip()), 'operator required')
    require(not output.exists(), 'output already exists; use a new run directory')
    require(all(not output.resolve().is_relative_to(p.resolve()) for p in protected),
            'output must not be inside immutable inputs')


def _contract_require(condition: bool, message: str) -> None:
    if not condition:
        raise BackendContractError(message)


def _check_result_identity(result: dict, request: dict) -> None:
    """Check transport identity and nullable diagnostics; do not redo B matching."""
    inputs = request['inputs']
    d = result['diagnostics']
    expected = {'condition_id': request['condition_id'], 'method_id': request['method_id'],
                'release_id': inputs['release_id'], 'query_count': len(inputs['query_ids']),
                'candidate_count': len(inputs['candidate_ids']), 'protocol_version': '1.0',
                'dimension': inputs['mri_descriptors'].shape[1]}
    _contract_require(all(d.get(k) == v for k, v in expected.items()), 'backend output identity differs from bound request')
    _contract_require(d['matching_config'] == request['config']['matching'], 'backend changed matching configuration')
    _contract_require([q['query_id'] for q in result['queries']] == inputs['query_ids'], 'backend query IDs/order differ')
    for q in result['queries']:
        _contract_require(q['condition_id'] == request['condition_id'] and q['method_id'] == request['method_id'],
                'mixed query output identities')
        _contract_require((q['ratio'] is None and q['ratio_pass'] is None)
                or (q['ratio'] is not None and type(q['ratio_pass']) is bool),
                'undefined ratio requires ratio_pass=null; backend contract repair needed')


def _execute(request: dict, backend, api: str, output: Path, run_id: str, operator: str, command: str) -> dict:
    identity = _code_identity(backend)
    started = datetime.now(timezone.utc).isoformat()
    inputs = request['inputs']
    arguments = {k: request[k] for k in ('condition_id', 'method_id', 'config')}
    if api == 'match_inputs':
        result = backend.match_inputs(inputs, **arguments)
    else:
        result = backend.match_descriptors(inputs['mri_descriptors'], inputs['us_descriptors'],
            inputs['query_ids'], inputs['candidate_ids'], inputs['candidate_source_rows'],
            release_id=inputs['release_id'], **arguments)
    try:
        _check_result_identity(result, request)
    except (KeyError, TypeError, AttributeError):
        raise BackendContractError('backend output schema differs') from None
    result = copy.deepcopy(result)
    result['diagnostics']['input_kind'] = request['kind']
    result['diagnostics']['request_schema'] = request['request_schema']
    result['diagnostics']['runner_source'] = identity
    for name, value in request['provenance'].items():
        key = 'verified_' + name
        _contract_require(key not in result['diagnostics']['input_sha256'], 'backend reused A provenance field')
        result['diagnostics']['input_sha256'][key] = value
    metadata = {'run_id': run_id, 'source_commit': identity['source_commit'],
        'source_dirty': identity['source_dirty'], 'mode': 'debug', 'operator': operator,
        'command': command, 'dependencies': {'python': platform.python_version(), 'numpy': np.__version__},
        'started_at': started, 'ended_at': datetime.now(timezone.utc).isoformat()}
    try:
        backend.write_match_outputs(result, output, run_metadata=metadata)
    except (ValueError, KeyError, TypeError) as error:
        raise BackendContractError('backend writer rejected output: ' + str(error)) from None
    run = read_json(output / 'RUN.json')
    _contract_require(all(run.get(k) == v for k, v in metadata.items()), 'backend RUN metadata differs')
    _contract_require(all(run['input_sha256'].get('verified_' + k) == v for k, v in request['provenance'].items()),
            'backend RUN lost verified input provenance')
    for name in ('queries.csv', 'pairs.csv', 'match_diagnostics.json'):
        _contract_require(digest((output / name).read_bytes()) == run['output_sha256'][name], 'output hash mismatch')
    return {'status': 'MATCH_COMPLETED_DEBUG', 'kind': request['kind'], 'run_id': run_id,
            'condition_id': request['condition_id'], 'method_id': request['method_id'],
            'query_count': len(result['queries']), 'accepted_count': len(result['pairs']),
            'source_commit': identity['source_commit'], 'source_dirty': identity['source_dirty'],
            'formal_matrix': 'NOT_RUN', 'algorithm_acceptance': 'NOT_ASSESSED'}


def match_release(release: Path, condition_id: str, method_id: str, expected_sha256: str,
                  output: Path, run_id: str, operator: str, input_kind='research_input') -> dict:
    """Run one explicitly requested debug match; no matrix or reference access."""
    _preflight(output, run_id, operator, [release])
    request = load_matching_request(release, condition_id, method_id, expected_sha256,
                                    expected_kind=input_kind)
    backend = _backend('match_inputs')
    command = f'mrus-missing match --release {release} --condition-id {condition_id} --method-id {method_id} --expected-sha256 {expected_sha256} --output {output} --run-id {run_id} --operator {operator} --input-kind {input_kind}'
    return _execute(request, backend, 'match_inputs', output, run_id, operator, command)


def match_fixture(fixture: Path, config: Path, method_id: str, output: Path, run_id: str, operator: str) -> dict:
    """Run a labelled small artificial example when B's API is in this checkout."""
    _preflight(output, run_id, operator, [fixture, config])
    require(fixture.stat().st_size <= 64 * 1024, 'fixture exceeds 64 KiB')
    raw, config_raw = fixture.read_bytes(), config.read_bytes()
    sample, settings = decode_json(raw), decode_json(config_raw)
    structure = validate_fixture(sample)
    validate_config(settings)
    require(method_id in ('MNN', 'MNN_RATIO'), 'unknown method')
    ids = structure['ordered_point_ids']
    keep = structure['kept_ids_in_source_order']
    rows = [ids['us'].index(p) for p in keep]
    inputs = {'mri_descriptors': np.asarray(sample['mri']['descriptors'], dtype=np.float32),
        'us_descriptors': np.asarray(sample['us']['descriptors'], dtype=np.float32)[rows],
        'query_ids': ids['mri'], 'candidate_ids': keep, 'candidate_source_rows': rows,
        'release_id': 'synthetic-' + digest(raw)[:16]}
    request = {'inputs': inputs, 'kind': 'synthetic_fixture', 'condition_id': 'SYNTHETIC_FIXTURE',
        'method_id': method_id, 'config': settings, 'request_schema': 'matching-request-v1',
        'provenance': {'fixture_file': digest(raw), 'experiment_file': digest(config_raw),
                       'condition_selection': digest(canonical(['SYNTHETIC_FIXTURE', keep, rows]))}}
    backend = _backend('match_descriptors')
    command = f'mrus-missing match-fixture --fixture {fixture} --config {config} --method-id {method_id} --output {output} --run-id {run_id} --operator {operator}'
    return _execute(request, backend, 'match_descriptors', output, run_id, operator, command)
