"""A's boundary/wiring tests. Test doubles do not validate B's numerical algorithm."""
import copy
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from test_preparation import source_case, prepared, reseal_release, replace_json
from mrus_missing.cli import main
from mrus_missing.errors import BackendContractError
import mrus_missing.matching_runner as runner
from mrus_missing.preparation import load_matching_inputs, load_matching_request
from mrus_missing.preparation.files import digest, read_json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/interface-v1.json'
CONFIG = ROOT / 'configs/experiment-v1.json'


@pytest.fixture
def bound_case(source_case):
    result = prepared(source_case)
    return source_case, result['input']['manifest_sha256']


def test_bound_request_keeps_legacy_six_fields_and_no_coordinate_reads(bound_case, monkeypatch):
    case, sha = bound_case
    import mrus_missing.preparation.release as module
    original = module.read_verified
    def guarded(root, spec):
        assert 'points' not in spec['path'] and 'reference' not in spec['path']
        return original(root, spec)
    monkeypatch.setattr(module, 'read_verified', guarded)
    request = load_matching_request(case['output'], 'RAND_2', 'MNN_RATIO', sha, expected_kind='synthetic_fixture')
    assert request['condition_id'] == 'RAND_2' and request['method_id'] == 'MNN_RATIO'
    assert set(request['inputs']) == {'mri_descriptors','us_descriptors','query_ids','candidate_ids','candidate_source_rows','release_id'}
    assert len(request['inputs']['candidate_ids']) == 48
    assert request['provenance']['release_manifest_file'] == sha
    legacy = load_matching_inputs(case['output'], 'RAND_2', sha, expected_kind='synthetic_fixture')
    assert legacy['candidate_ids'] == request['inputs']['candidate_ids']


@pytest.mark.parametrize('condition,method,sha_override', [
    ('NOT_A_CONDITION','MNN',None), ('FULL','NOT_A_METHOD',None),
    ('FULL','MNN','0'*64), ('FULL','MNN',''),
])
def test_bad_request_rejected(bound_case, condition, method, sha_override):
    case, sha = bound_case
    with pytest.raises(ValueError):
        load_matching_request(case['output'], condition, method,
                              sha if sha_override is None else sha_override, expected_kind='synthetic_fixture')


@pytest.mark.parametrize('field,value', [('ratio_threshold',.9),('eps',1e-8),('query_count',32),('dimension',128)])
def test_config_drift_even_with_resealed_manifest_rejected(bound_case, field, value):
    case, _ = bound_case
    path = case['output'] / 'experiment.json'
    config = read_json(path); config['matching'][field] = value; replace_json(path, config)
    mpath = case['output'] / 'manifest.json'; m = read_json(mpath)
    m['experiment_sha256'] = digest(path.read_bytes()); replace_json(mpath, m); reseal_release(case['output'])
    with pytest.raises(ValueError, match='configuration differs'):
        load_matching_request(case['output'],'FULL','MNN',digest(mpath.read_bytes()),expected_kind='synthetic_fixture')


def test_false_full_candidate_list_rejected(bound_case):
    case, _ = bound_case
    p = case['output'] / 'conditions.json'; c = read_json(p)
    full = c['conditions'][0]; full['remove_ids'] = full['keep_ids'][48:]; full['keep_ids'] = full['keep_ids'][:48]
    replace_json(p,c); reseal_release(case['output'])
    with pytest.raises(ValueError,match='partition'):
        load_matching_request(case['output'],'FULL','MNN',digest((case['output']/'manifest.json').read_bytes()),expected_kind='synthetic_fixture')


@pytest.fixture
def transport_double(monkeypatch):
    """A transport spy with no numerical matcher. It records and echoes identities."""
    seen = {}
    def inputs_api(inputs, *, condition_id, method_id, config):
        seen['inputs'] = inputs; seen['condition'] = condition_id; seen['config'] = config
        return {'queries':[{'query_id':pid,'query_row':i,'condition_id':condition_id,
                           'method_id':method_id,'ratio':None,'ratio_pass':None}
                          for i,pid in enumerate(inputs['query_ids'])], 'pairs':[],
                'diagnostics':{'status':'SUCCESS','condition_id':condition_id,'method_id':method_id,
                    'release_id':inputs['release_id'],'query_count':len(inputs['query_ids']),
                    'candidate_count':len(inputs['candidate_ids']),'dimension':inputs['mri_descriptors'].shape[1],
                    'protocol_version':'1.0','matching_config':copy.deepcopy(config['matching']),
                    'input_sha256':{'test_double_payload':'0'*64}}}
    def descriptor_api(q,u,qids,uids,rows,*,release_id,**kwargs):
        return inputs_api(dict(mri_descriptors=q,us_descriptors=u,query_ids=qids,candidate_ids=uids,
                               candidate_source_rows=rows,release_id=release_id),**kwargs)
    def writer(result, output, *, run_metadata):
        seen['writer_called'] = True; seen['result'] = result
        output.mkdir(parents=True,exist_ok=False)
        payloads={'queries.csv':'query_id\n','pairs.csv':'query_id,candidate_id\n',
                  'match_diagnostics.json':json.dumps(result['diagnostics'])}
        for name,text in payloads.items():(output/name).write_text(text,encoding='utf-8')
        run={**run_metadata, **{k:result['diagnostics'][k] for k in
                               ('release_id','condition_id','method_id','protocol_version','status')},
             'configuration':result['diagnostics']['matching_config'],
             'input_sha256':result['diagnostics']['input_sha256'],
             'output_sha256':{n:digest((output/n).read_bytes()) for n in payloads}}
        (output/'RUN.json').write_text(json.dumps(run),encoding='utf-8')
        return run
    backend=SimpleNamespace(match_inputs=inputs_api,match_descriptors=descriptor_api,write_match_outputs=writer)
    monkeypatch.setattr(runner,'_backend',lambda api:backend)
    monkeypatch.setattr(runner,'_code_identity',lambda b:dict(source_commit='a'*40,source_dirty=True,files_sha256={'test-double':'b'*64}))
    return backend,seen


def test_runner_passes_one_bound_request_and_records_provenance(bound_case, transport_double, tmp_path):
    case,sha=bound_case; _,seen=transport_double
    out=tmp_path/'run'
    result=runner.match_release(case['output'],'RAND_2','MNN_RATIO',sha,out,'synthetic-run','test-reviewer','synthetic_fixture')
    assert result['kind']=='synthetic_fixture' and result['source_dirty'] is True
    assert seen['condition']=='RAND_2' and seen['config']['matching']['ratio_threshold']==.8
    assert len(seen['inputs']['candidate_ids'])==48
    run=read_json(out/'RUN.json')
    assert run['input_sha256']['verified_release_manifest_file']==sha and run['mode']=='debug'
    assert {k:run[k] for k in ('release_id','condition_id','method_id','protocol_version','status')} == {
        'release_id':seen['inputs']['release_id'], 'condition_id':'RAND_2',
        'method_id':'MNN_RATIO', 'protocol_version':'1.0', 'status':'SUCCESS'}


@pytest.mark.parametrize('location', ['run', 'diagnostics', 'both'])
@pytest.mark.parametrize('field,bad_value', [
    ('release_id','another-release'), ('condition_id','FULL'), ('method_id','MNN'),
    ('protocol_version','9.9'), ('status','FAILURE'),
])
def test_persisted_identity_corruption_rejected(bound_case, transport_double, tmp_path,
                                               location, field, bad_value):
    case, sha = bound_case
    backend, _ = transport_double
    original = backend.write_match_outputs
    def corrupt(result, output, *, run_metadata):
        run = original(result, output, run_metadata=run_metadata)
        if location in ('run', 'both'):
            run[field] = bad_value
        if location in ('diagnostics', 'both'):
            path = output / 'match_diagnostics.json'
            diagnostics = read_json(path)
            diagnostics[field] = bad_value
            replace_json(path, diagnostics)
            # A self-consistent hash must not conceal wrong experiment identity.
            run['output_sha256'][path.name] = digest(path.read_bytes())
            result['diagnostics'][field] = bad_value
        replace_json(output / 'RUN.json', run)
        return run
    backend.write_match_outputs = corrupt
    with pytest.raises(BackendContractError, match='identity/status'):
        runner.match_release(case['output'], 'RAND_1', 'MNN_RATIO', sha,
                             tmp_path / 'bad-run', 'run-review', 'tester', 'synthetic_fixture')


@pytest.mark.parametrize('mutation', ['missing_field', 'bad_json', 'not_object', 'bad_hash_map', 'missing_file'])
def test_malformed_run_is_backend_contract_error(bound_case, transport_double, tmp_path, mutation):
    case, sha = bound_case
    backend, _ = transport_double
    original = backend.write_match_outputs
    def corrupt(result, output, *, run_metadata):
        run = original(result, output, run_metadata=run_metadata)
        path = output / 'RUN.json'
        if mutation == 'missing_field':
            run.pop('condition_id'); replace_json(path, run)
        elif mutation == 'bad_json':
            path.write_text('{invalid', encoding='utf-8')
        elif mutation == 'not_object':
            replace_json(path, [])
        elif mutation == 'bad_hash_map':
            run['output_sha256'] = []; replace_json(path, run)
        else:
            path.unlink()
        return run
    backend.write_match_outputs = corrupt
    with pytest.raises(BackendContractError):
        runner.match_release(case['output'], 'RAND_1', 'MNN_RATIO', sha,
                             tmp_path / 'bad-run', 'run-review', 'tester', 'synthetic_fixture')


def test_persisted_run_error_exits_four(transport_double, tmp_path, capsys):
    backend, _ = transport_double
    original = backend.write_match_outputs
    def corrupt(result, output, *, run_metadata):
        run = original(result, output, run_metadata=run_metadata)
        run['condition_id'] = 'FULL'
        replace_json(output / 'RUN.json', run)
        return run
    backend.write_match_outputs = corrupt
    assert main(['match-fixture','--fixture',str(FIXTURE),'--config',str(CONFIG),'--method-id','MNN',
                 '--output',str(tmp_path/'output'),'--run-id','fixture-bad-run','--operator','tester']) == 4
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err)['status'] == 'BACKEND_CONTRACT_ERROR'


@pytest.mark.parametrize('bad_kind',['identity','config','nullable'])
def test_bad_backend_result_rejected_before_writing(bound_case, transport_double, tmp_path, bad_kind):
    case,sha=bound_case; backend,seen=transport_double
    original=backend.match_inputs
    def bad(*args,**kwargs):
        r=original(*args,**kwargs)
        if bad_kind=='identity':r['diagnostics']['condition_id']='FULL'
        if bad_kind=='config':r['diagnostics']['matching_config']['ratio_threshold']=.9
        if bad_kind=='nullable':r['queries'][0]['ratio_pass']=False
        return r
    backend.match_inputs=bad
    with pytest.raises(ValueError):
        runner.match_release(case['output'],'RAND_1','MNN',sha,tmp_path/'bad','synthetic-run','tester','synthetic_fixture')
    assert not seen.get('writer_called') and not (tmp_path/'bad').exists()


def test_overwrite_source_write_and_wrong_kind_rejected(bound_case,transport_double,tmp_path):
    case,sha=bound_case
    existing=tmp_path/'keep'; existing.mkdir(); (existing/'note').write_text('keep')
    for output,kind in [(existing,'synthetic_fixture'),(case['output']/'bad','synthetic_fixture'),(tmp_path/'bad','research_input')]:
        with pytest.raises(ValueError):runner.match_release(case['output'],'FULL','MNN',sha,output,'r1','tester',kind)
    assert (existing/'note').read_text()=='keep' and not (tmp_path/'bad').exists()


def test_fixture_cli_wiring_with_transport_double(transport_double,tmp_path,capsys):
    assert main(['match-fixture','--fixture',str(FIXTURE),'--config',str(CONFIG),'--method-id','MNN',
                 '--output',str(tmp_path/'output'),'--run-id','fixture-001','--operator','tester'])==0
    assert json.loads(capsys.readouterr().out)['kind']=='synthetic_fixture'


def test_release_cli_uses_bound_labels(bound_case,transport_double,tmp_path,capsys):
    case,sha=bound_case; _,seen=transport_double
    assert main(['match','--release',str(case['output']),'--condition-id','RAND_3',
                 '--method-id','MNN_RATIO','--expected-sha256',sha,'--output',str(tmp_path/'output'),
                 '--run-id','synthetic-003','--operator','tester','--input-kind','synthetic_fixture'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['condition_id']=='RAND_3' and seen['condition']=='RAND_3'


def test_missing_backend_is_explicit_and_writes_nothing(monkeypatch,tmp_path,capsys):
    monkeypatch.setattr(runner.importlib,'import_module',lambda name:SimpleNamespace())
    assert main(['match-fixture','--fixture',str(FIXTURE),'--config',str(CONFIG),'--method-id','MNN',
                 '--output',str(tmp_path/'output'),'--run-id','fixture-001','--operator','tester'])==3
    assert 'B_matching_backend' in json.loads(capsys.readouterr().err)['stage']
    assert not (tmp_path/'output').exists()


def test_status_does_not_claim_scientific_completion(capsys):
    assert main(['status'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['execution_by_status'] is False and result['scientific_run_history']=='NOT_INSPECTED'


def test_cli_distinguishes_backend_contract_from_bad_inputs(transport_double,tmp_path,capsys):
    backend,_=transport_double;original=backend.match_descriptors
    def bad(*args,**kwargs):
        result=original(*args,**kwargs);result['queries'][0]['ratio_pass']=False
        return result
    backend.match_descriptors=bad
    assert main(['match-fixture','--fixture',str(FIXTURE),'--config',str(CONFIG),'--method-id','MNN',
                 '--output',str(tmp_path/'bad'),'--run-id','fixture-bad','--operator','tester'])==4
    assert json.loads(capsys.readouterr().err)['status']=='BACKEND_CONTRACT_ERROR'
    assert not (tmp_path/'bad').exists()


@pytest.mark.skipif(not runner.matching_capabilities()['match_fixture'],reason='B API not present in this branch')
@pytest.mark.parametrize('method',['MNN','MNN_RATIO'])
def test_actual_backend_fixture_end_to_end(method,tmp_path):
    """Runs after B is present; it is an A seam check, not B's boundary test suite."""
    result=runner.match_fixture(FIXTURE,CONFIG,method,tmp_path/'output','fixture-smoke','test-reviewer')
    assert result['kind']=='synthetic_fixture' and result['query_count']==4
    assert result['accepted_count']==3
