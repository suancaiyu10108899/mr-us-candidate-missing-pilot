"""Production preparation exercised on explicitly synthetic source artifacts."""
import copy
import io
import json
import math
from pathlib import Path
import shutil
from zipfile import ZipFile

import numpy as np
import pytest

from mrus_missing.cli import main
from mrus_missing.preparation import (load_geometry_points, load_matching_inputs, prepare,
                                      verify_inputs, verify_reference)
from mrus_missing.preparation.delivery import package_inputs
from mrus_missing.preparation.files import canonical, digest, file_specs, read_json, seal, write_json
from mrus_missing.preparation.legacy import audit_source
from mrus_missing.preparation.release import build_conditions

ROOT = Path(__file__).resolve().parents[1]


def npy(array):
    stream = io.BytesIO()
    np.save(stream, array, allow_pickle=False)
    return stream.getvalue()


@pytest.fixture
def source_case(tmp_path):
    source = tmp_path / 'old'
    source.mkdir()
    artifacts = {}
    provenance = {'scientific_source_commit': 'a' * 40, 'checkpoint_sha256': 'b' * 64,
                  'encoder_id': 'synthetic-encoder', 'preprocess_id': 'synthetic-preprocess'}

    def artifact(name, kind, meta, payloads, parents=()):
        folder = source / name
        folder.mkdir()
        for filename, blob in payloads.items():
            (folder / filename).write_bytes(blob)
        specs = {Path(f).stem: s for f, s in file_specs(folder, list(payloads)).items()}
        m = seal({'schema_version': 'pilot-v1', 'artifact_id': name, 'artifact_type': kind,
                  'code_commit': provenance['scientific_source_commit'], 'meta': meta,
                  'payloads': specs, 'parents': list(parents)})
        write_json(folder / 'manifest.json', m)
        artifacts[name] = {'path': name, 'manifest_sha256': digest((folder / 'manifest.json').read_bytes()),
                           'artifact_id': name, 'artifact_type': kind, 'content_sha256': m['content_sha256']}
        return {'artifact_id': name, 'content_sha256': m['content_sha256']}

    xyz = np.array([[i % 4 * 3, i // 4 % 4 * 3, i // 16 * 3] for i in range(64)], dtype=np.float64)
    us = xyz + [4., -3., 2.]
    queries, candidates = [f'q{i:02}' for i in range(64)], [f'u{i:02}' for i in range(64)]
    order = [(i * 17 + 3) % 64 for i in range(64)]
    vectors = np.eye(64, 512, dtype=np.float32)
    points, descriptors = {}, {}
    for side, ids, coords, permutation, modality in (
        ('mri', queries, xyz, list(range(64)), 'MRI'), ('us', candidates, us, order, 'US')):
        points[side] = artifact(side + '_points', 'PointSet', {
            'point_ids': ids[::-1], 'frame_id': side, 'unit': 'index_unit',
            'coordinate_order': ['I', 'J', 'K'], 'coordinates_payload': 'coordinates'},
            {'coordinates.npy': npy(coords[::-1])})
        descriptors[side] = artifact(side + '_descriptors', 'DescriptorSet', {
            **{k: v for k, v in provenance.items() if k != 'scientific_source_commit'},
            'producer_type': 'MODEL_TRAINED', 'modality': modality, 'point_ids': [ids[i] for i in permutation],
            'pointset': points[side], 'frame_id': side, 'vectors_payload': 'vectors'},
            {'vectors.npy': npy(vectors[permutation])}, [points[side]])
    reference = {'visibility': 'eval-only', 'unit': 'index_unit', 'source_frame_id': 'us',
        'target_frame_id': 'mri', 'pointset_ids': {'MRI': 'mri_points', 'U_SHIFT': 'us_points'},
        'R': np.eye(3).tolist(), 't': [-4., 3., -2.], 'correctness_threshold': .5,
        'mr_ids': queries, 'us_ids': candidates, 'probes_us': us[[0,3,12,15,48,51,60,63]].tolist(),
        'probes_mr': xyz[[0,3,12,15,48,51,60,63]].tolist()}
    artifact('reference', 'VolumeRelease', {'evaluation_reference_payload': 'evaluation_reference'},
             {'evaluation_reference.json': canonical(reference)})
    pairs = [{'mr_id': queries[i], 'us_id': candidates[i], 'distance': 0.,
              'second_distance': math.sqrt(2), 'ratio': 0.} for i in range(47)]
    match = artifact('baseline_pairs', 'MatchSet', {'mr_pointset': points['mri'], 'us_pointset': points['us'],
        'distance_metric': 'L2', 'ratio_threshold': .8, 'mutual': True, 'status': 'SUCCESS',
        'accepted_count': 47, 'pairs_payload': 'pairs'}, {'pairs.json': canonical(pairs)}, list(descriptors.values()))
    artifact('baseline_transform', 'Transform', {'status': 'SUCCESS', 'direction': 'US_TO_MR',
        'unit': 'index_unit', 'R': np.eye(3).tolist(), 't': [-4.,3.,-2.]}, {}, [match, *points.values()])
    lock = {**provenance, 'schema_version': 'source-lock-v1', 'kind': 'synthetic_fixture',
        'release_id': 'synthetic-test-v1', 'source_snapshot_commit': 'c' * 40, 'shape': [64,512],
        'artifacts': artifacts, 'attribution': {'kind': 'synthetic_fixture', 'origin': 'created by test'}}
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    config = config_dir / 'experiment-v1.json'
    shutil.copyfile(ROOT / 'configs/experiment-v1.json', config)
    write_json(config_dir / 'source-crosskey-v1.json', lock)
    return {'source': source, 'lock': lock, 'config': config, 'output': tmp_path / 'release',
            'reference_output': tmp_path / 'reference'}


def prepared(case):
    return prepare(**{k: v for k, v in case.items() if k != 'lock'})


def replace_json(path, data):
    path.write_text(json.dumps(data, allow_nan=False), encoding='utf-8')


def reseal_source(case, name, edit):
    path = case['source'] / name / 'manifest.json'
    m = read_json(path)
    edit(m)
    m.pop('content_sha256')
    m = seal(m)
    replace_json(path, m)
    case['lock']['artifacts'][name]['manifest_sha256'] = digest(path.read_bytes())
    case['lock']['artifacts'][name]['content_sha256'] = m['content_sha256']


def reseal_release(root, name='manifest.json'):
    m = read_json(root / name)
    m['files'] = file_specs(root, list(m['files']))
    m.pop('content_sha256')
    replace_json(root / name, seal(m))


def test_prepare_preserves_source_bytes_and_row_identity(source_case):
    c = source_case
    before = {p.relative_to(c['source']): digest(p.read_bytes()) for p in c['source'].rglob('*') if p.is_file()}
    r = prepared(c)
    assert r['audit']['historical_pairs_checked'] == 47
    assert r['audit']['original_probes_checked'] == 8
    assert r['audit']['new_matching_run'] == 'NOT_RUN'
    assert r['input']['kind'] == 'synthetic_fixture'
    for relative, sha in before.items():
        assert digest((c['source'] / relative).read_bytes()) == sha
    for side in ('mri','us'):
        assert (c['output']/f'{side}_descriptors.npy').read_bytes() == (c['source']/f'{side}_descriptors/vectors.npy').read_bytes()
    geometry = load_geometry_points(c['output'], expected_kind='synthetic_fixture')
    assert np.array_equal(geometry['mri']['q00'], [0.,0.,0.])
    assert np.array_equal(geometry['us']['u00'], [4.,-3.,2.])
    assert not {'reference.json','baseline_pairs.csv'} & {p.name for p in c['output'].iterdir()}
    with pytest.raises(ValueError, match='synthetic'):
        verify_inputs(c['output'])


def test_source_bad_hash_stops_before_output(source_case):
    c=source_case
    p=c['source']/'mri_descriptors/vectors.npy'
    p.write_bytes(p.read_bytes()[:-1]+b'!')
    with pytest.raises(ValueError, match='SHA'):
        prepared(c)
    assert not c['output'].exists() and not c['reference_output'].exists()


@pytest.mark.parametrize('name,edit,reason', [
    ('mri_descriptors',lambda m:m['meta'].update(producer_type='MODEL_INIT'),'trained'),
    ('mri_descriptors',lambda m:m['meta'].update(encoder_id='another-model'),'identity'),
    ('mri_descriptors',lambda m:m['meta']['point_ids'].__setitem__(0,m['meta']['point_ids'][1]),'IDs'),
    ('mri_descriptors',lambda m:m['meta']['pointset'].update(content_sha256='0'*64),'parent'),
    ('us_points',lambda m:m['meta'].update(unit='mm'),'frame/unit'),
    ('mri_descriptors',lambda m:m['payloads']['vectors'].update(path='../elsewhere.npy'),'unsafe'),
])
def test_semantically_invalid_source_even_with_valid_hash(source_case,name,edit,reason):
    reseal_source(source_case,name,edit)
    if name == 'us_points':
        binding={k:source_case['lock']['artifacts'][name][k] for k in ('artifact_id','content_sha256')}
        reseal_source(source_case,'us_descriptors',lambda m:(m['meta'].update(pointset=binding),m.update(parents=[binding])))
    with pytest.raises(ValueError,match=reason):
        audit_source(source_case['source'],source_case['lock'])


def test_nonfinite_payload_with_valid_hash_rejected(source_case):
    c=source_case
    p=c['source']/'mri_descriptors/vectors.npy'
    a=np.load(p,allow_pickle=False);a[0,0]=np.nan;p.write_bytes(npy(a))
    reseal_source(c,'mri_descriptors',lambda m:m['payloads']['vectors'].update(sha256=digest(p.read_bytes())))
    with pytest.raises(ValueError,match='nonfinite'):
        audit_source(c['source'],c['lock'])


def test_source_reference_unique_geometry_required(source_case):
    c=source_case
    p=c['source']/'us_points/coordinates.npy'
    a=np.load(p,allow_pickle=False);a[1]=a[0];p.write_bytes(npy(a))
    reseal_source(c,'us_points',lambda m:m['payloads']['coordinates'].update(sha256=digest(p.read_bytes())))
    new_id={k:c['lock']['artifacts']['us_points'][k] for k in ('artifact_id','content_sha256')}
    reseal_source(c,'us_descriptors',lambda m:(m['meta'].update(pointset=new_id),m.update(parents=[new_id])))
    with pytest.raises(ValueError,match='unique'):
        audit_source(c['source'],c['lock'])


def test_no_overwrite_or_source_write(source_case):
    c=source_case
    c['output'].mkdir()
    (c['output']/'keep.txt').write_text('preserve')
    with pytest.raises(ValueError,match='exists'):
        prepared(c)
    assert (c['output']/'keep.txt').read_text()=='preserve'
    c['output']=c['source']/'new'
    with pytest.raises(ValueError,match='source tree'):
        prepared(c)


def test_matching_reader_does_not_read_coordinates_or_answers(source_case,monkeypatch):
    c=source_case;prepared(c)
    import mrus_missing.preparation.release as module
    original=module.read_verified
    def guarded(root,spec):
        assert 'points' not in spec['path'] and 'reference' not in spec['path']
        return original(root,spec)
    monkeypatch.setattr(module,'read_verified',guarded)
    data=load_matching_inputs(c['output'],'RAND_1',expected_kind='synthetic_fixture')
    assert data['mri_descriptors'].shape==(64,512) and data['us_descriptors'].shape==(48,512)
    assert not {'reference','points','baseline_pairs'} & data.keys()
    assert data['candidate_source_rows']==sorted(data['candidate_source_rows'])


@pytest.mark.parametrize('mutation', ['duplicate_id','missing_row','nonfinite','overlap','unknown','duplicate_candidate'])
def test_release_semantics_cannot_be_hidden_by_resealing(source_case,mutation):
    c=source_case;prepared(c)
    if mutation in ('duplicate_id','missing_row','nonfinite'):
        from mrus_missing.preparation.files import read_csv,write_csv
        p=c['output']/'mri_points.csv';rows=read_csv(p)
        if mutation=='duplicate_id':rows[1]['point_id']=rows[0]['point_id']
        if mutation=='missing_row':rows[1]['descriptor_row']='999'
        if mutation=='nonfinite':rows[1]['i']='nan'
        p.unlink();write_csv(p,rows,list(rows[0]))
    else:
        p=c['output']/'conditions.json';v=read_json(p);item=v['conditions'][1]
        if mutation=='overlap':item['remove_ids'][0]=item['keep_ids'][0]
        if mutation=='unknown':item['keep_ids'][0]='unknown'
        if mutation=='duplicate_candidate':item['keep_ids'][0]=item['keep_ids'][1]
        replace_json(p,v)
    reseal_release(c['output'])
    with pytest.raises(ValueError):verify_inputs(c['output'],expected_kind='synthetic_fixture')


def test_point_csv_display_order_is_not_descriptor_order(source_case):
    c=source_case;prepared(c)
    expected=load_geometry_points(c['output'],expected_kind='synthetic_fixture')
    from mrus_missing.preparation.files import read_csv,write_csv
    p=c['output']/'mri_points.csv';rows=read_csv(p);p.unlink();write_csv(p,rows[::-1],list(rows[0]))
    reseal_release(c['output'])
    actual=load_geometry_points(c['output'],expected_kind='synthetic_fixture')
    assert all(np.array_equal(v,actual['mri'][k]) for k,v in expected['mri'].items())


def test_handoff_hash_and_reference_binding(source_case):
    c=source_case;r=prepared(c)
    verify_inputs(c['output'],r['input']['manifest_sha256'],expected_kind='synthetic_fixture')
    with pytest.raises(ValueError,match='external'):
        verify_inputs(c['output'],'0'*64,expected_kind='synthetic_fixture')
    p=c['reference_output']/'reference_manifest.json';m=read_json(p)
    m['input_manifest_sha256']='0'*64;m.pop('content_sha256');replace_json(p,seal(m))
    with pytest.raises(ValueError,match='mixed'):
        verify_reference(c['reference_output'],c['output'],expected_kind='synthetic_fixture')


def test_packaging_separates_answers_and_roundtrips(source_case,tmp_path):
    c=source_case;prepared(c)
    first=package_inputs(c['output'],c['reference_output'],tmp_path/'delivery1',expected_kind='synthetic_fixture')
    second=package_inputs(c['output'],c['reference_output'],tmp_path/'delivery2',expected_kind='synthetic_fixture')
    assert first==second
    inp=tmp_path/'unpacked-input';ref=tmp_path/'unpacked-ref'
    with ZipFile(tmp_path/'delivery1'/first['archives']['inputs_for_B_C_D']['filename']) as z:
        assert not {'reference.json','baseline_pairs.csv'} & set(z.namelist())
        z.extractall(inp)  # Trusted archive generated by the production function in this test.
    with ZipFile(tmp_path/'delivery1'/first['archives']['reference_for_A_D']['filename']) as z:z.extractall(ref)
    verify_inputs(inp,first['input_manifest_sha256'],expected_kind='synthetic_fixture')
    verify_reference(ref,inp,first['reference_manifest_sha256'],expected_kind='synthetic_fixture')


def _set_release_identity(case, release_id):
    """Keep artificial envelopes/binding self-consistent, independent of name safety."""
    path = case['output'] / 'manifest.json'
    manifest = read_json(path)
    manifest['release_id'] = release_id
    manifest.pop('content_sha256')
    replace_json(path, seal(manifest))
    reference_path = case['reference_output'] / 'reference_manifest.json'
    reference = read_json(reference_path)
    reference.update(release_id=release_id, input_manifest_sha256=digest(path.read_bytes()))
    reference.pop('content_sha256')
    replace_json(reference_path, seal(reference))


@pytest.mark.parametrize('release_id', [
    '../escaped-review', r'..\escaped-review', '/escaped-review', r'C:\escaped-review',
    'nested/release', '', '.', '..', 'a' * 65, None, 42,
])
def test_packaging_rejects_unsafe_release_id_before_writing(source_case, tmp_path, release_id):
    prepared(source_case)
    _set_release_identity(source_case, release_id)
    output = tmp_path / 'delivery'
    with pytest.raises(ValueError, match='invalid release ID'):
        package_inputs(source_case['output'], source_case['reference_output'], output,
                       expected_kind='synthetic_fixture')
    assert not output.exists()
    assert not list(tmp_path.rglob('*.zip'))


@pytest.mark.parametrize('release_id', ['release.v1_A-9', 'a' * 64])
def test_packaging_safe_release_id_stays_inside_output(source_case, tmp_path, release_id):
    prepared(source_case)
    _set_release_identity(source_case, release_id)
    output = tmp_path / 'delivery'
    result = package_inputs(source_case['output'], source_case['reference_output'], output,
                            expected_kind='synthetic_fixture')
    assert result['release_id'] == release_id
    archives = list(tmp_path.rglob('*.zip'))
    assert {p.name for p in archives} == {release_id + '-inputs.zip', release_id + '-reference.zip'}
    assert all(p.parent.resolve() == output.resolve() for p in archives)


def test_prepare_uses_same_release_id_validation(source_case):
    source_case['lock']['release_id'] = None
    replace_json(source_case['config'].parent / 'source-crosskey-v1.json', source_case['lock'])
    with pytest.raises(ValueError, match='invalid release ID'):
        prepared(source_case)
    assert not source_case['output'].exists() and not source_case['reference_output'].exists()


def test_packaging_preserves_existing_delivery(source_case, tmp_path):
    prepared(source_case)
    output = tmp_path / 'delivery'
    package_inputs(source_case['output'], source_case['reference_output'], output,
                   expected_kind='synthetic_fixture')
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError, match='never overwrite'):
        package_inputs(source_case['output'], source_case['reference_output'], output,
                       expected_kind='synthetic_fixture')
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_cli_prepare_calls_real_implementation(source_case,capsys):
    c=source_case
    args=['prepare','--source',str(c['source']),'--config',str(c['config']),
          '--output',str(c['output']),'--reference-output',str(c['reference_output'])]
    assert main(args)==0
    assert json.loads(capsys.readouterr().out)['status']=='PREPARED'
    assert main(args)==2
    assert json.loads(capsys.readouterr().err)['status']=='INVALID_INPUT'
