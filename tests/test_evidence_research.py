import csv
import hashlib
import io
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook
from app import app
from services.frames import parse_frames, convert_frame
from services.evidence import METADATA_COLUMNS, evidence_index
from services.evaluation import evaluate
from tests.workbook_helpers import records

ROOT = Path(__file__).resolve().parents[1]
OLD_SHEETS = ['보완합계', '보완근거', 'Results', 'MedicationResults', 'Review', 'AuditTrail', '코드안내']


def test_metadata_complete_grade_honest_factors_preserved_and_rebuild_idempotent(tmp_path, monkeypatch):
    import scripts.build_equivalence_lookup as builder
    content = (ROOT/'lookup/master_lookup.csv').read_bytes().replace(b'\r\n', b'\n')
    rows = list(csv.DictReader(io.StringIO(content.decode())))
    assert all(all(r[k] for k in METADATA_COLUMNS) for r in rows)
    assert {r['evidence_grade'] for r in rows} == {'not_assessed'}
    # All original method/drug/factor strings, including their precision, are frozen.
    numeric = '\n'.join(','.join(r[k] for k in ('method_id','source_drug','target_drug','factor')) for r in rows) + '\n'
    manifest = json.loads((ROOT/'data/evaluation/baseline_factors.json').read_text())
    assert hashlib.sha256(numeric.encode()).hexdigest() == manifest['rows_sha256']
    (tmp_path/'lookup').mkdir()
    (tmp_path/'lookup/master_lookup.csv').write_bytes(content)
    (tmp_path/'lookup/equivalence_anchors.csv').write_bytes((ROOT/'lookup/equivalence_anchors.csv').read_bytes())
    monkeypatch.setattr(builder, 'ROOT', tmp_path)
    builder.build()
    assert (tmp_path/'lookup/master_lookup.csv').read_bytes() == content


def test_evidence_follows_actual_injection_path_and_missing_factors():
    item = convert_frame(parse_frames('Sustenna 156mg monthly')[0], ['DDD','MED','CMD'])
    evidence = {c['method']:c['evidence'] for c in item['conversions']}
    assert evidence['DDD']['calculation_basis'] == 'route_specific_DDD'
    assert 'atcddd' in evidence['DDD']['evidence_source']
    assert evidence['DDD']['active_moiety_mg'] == 100
    assert evidence['MED']['calculation_basis'] == 'label_oral_bridge_estimate'
    assert evidence['MED']['oral_bridge_source']
    assert evidence['CMD']['available'] is False and evidence['CMD']['unavailable_reason']
    assert item['needs_review'] is False
    missing = convert_frame(parse_frames('unknownxyz 5mg')[0], ['CMD','MED'])
    assert all(not e['available'] for e in json.loads(missing['factor_evidence']))
    assert len(json.loads(missing['factor_evidence'])) == 2
    assert 'clozapine' in evidence_index()['CMD','clozapine','olanzapine']['exclusion_conditions']


@pytest.mark.parametrize('text', ['quetiapine take 1/2 tablet (50 mg) every day',
    'risperidone 2mg/mL QD', 'risperidone 2-3mg QD', 'risperidone 2mg q2-3hr',
    'quetiapine ½ tablet (50mg) QD'])
def test_ambiguous_fraction_concentration_and_ranges_abstain(text):
    items = [convert_frame(f, ['DDD','MED']) for f in parse_frames(text)]
    assert not any(c['value'] is not None for i in items for c in i['conversions'])


@pytest.mark.parametrize('source', [
    'patient_id,medication\n001,risperidone 2mg QD\n002,paliperidone 6mg QD\n003,unknownxyz 5mg\n004,lithium 600mg\n',
    'HID,PRESCR_DATE,DRUG,TABS_PER_DAY\n001,2026-10-19,Risperidone 2mg tab,1\n002,2026-10-19,Paliperidone 6mg tab,1\n003,2026-10-19,unknownxyz 5mg tab,1\n004,2026-10-19,Lithium 600mg tab,1\n'
])
def test_export_keeps_six_sheets_even_with_obsolete_options(source):
    def export(opt):
        r=app.test_client().post('/upload',data={'file':(io.BytesIO(source.encode()),'synthetic.csv'), 'include_sensitivity':opt})
        assert r.status_code == 200, r.data[:1000]
        return load_workbook(io.BytesIO(r.data))
    ordinary, legacy_request = export(''), export('yes')
    assert ordinary.sheetnames == OLD_SHEETS
    assert legacy_request.sheetnames == OLD_SHEETS
    for name in OLD_SHEETS:
        assert list(ordinary[name].values) == list(legacy_request[name].values)
    for ws in ordinary:
        assert ws.freeze_panes is None and ws.auto_filter.ref.startswith('A1:')
    assert all('factor_evidence' in r for r in records(ordinary, 'AuditTrail'))


def test_evaluation_counts_wrong_answers_missing_fields_false_alerts_and_both_directions():
    cases=[dict(id=str(i), text=str(i), should_convert=i<3, normal=i<3,
                gold=[dict(drug='risperidone',unit='mg',daily_dose_mg=2)], drug_class='antipsychotic') for i in range(4)]
    def predictor(text):
        i=int(text)
        return [dict(drug='risperidone',unit='g' if i==1 else 'mg', daily_dose_mg=[2,2000,1,None][i],
                     ok=i<3,needs_review=i in (0,3),conversions=[dict(value=1)] if i<3 else [])]
    result=evaluate(cases,predictor)
    assert result['unit_accuracy']['accuracy']==.75
    assert result['overall']['strict_output']==dict(tp=1,fp=2,fn=2,ppv=1/3,sensitivity=1/3,f1=1/3)
    assert result['overall']['dose_direction']==dict(over=1,under=1,equal=1,missing=1,wrong_drug=0)
    assert result['overall']['false_alert_rate']==1/3
    assert result['overall']['abstention_accuracy']==1
    assert result['external_api_cost_usd'] is None
    assert evaluate([])['unit_accuracy']['accuracy'] is None


def test_evidence_download_and_pages_are_available():
    client=app.test_client()
    assert client.get('/methods').status_code==200
    methods=client.get('/api/methods').json['methods']
    assert len(methods)==10
    assert next(m for m in methods if m['method']=='INADA')['source'].endswith('/25601291/')
    assert b'evidence_grade' in client.get('/evidence.csv').data
    assert b'include_sensitivity' not in client.get('/').data
    assert '방법별 민감도 분석' not in client.get('/methods').get_data(as_text=True)
    assert 'sensitivity_version' not in client.get('/version').json
    assert client.get('/version').json['evidence_grade_policy']=='not_assessed_no_inferred_GRADE'


@pytest.mark.parametrize('text', ['risperidone 2000㎍ QD', 'risperidone 2㎎ QD'])
def test_deterministic_unit_normalization_is_a_note_not_a_false_alert(text):
    item=convert_frame(parse_frames(text)[0], ['DDD'])
    assert item['daily_dose_mg']==2
    assert not item['needs_review'] and not item['warning']
    assert '정규화' in item['calculation_note']


def test_quick_export_keeps_six_sheets_with_obsolete_options():
    response=app.test_client().post('/api/export', json={'text':'risperidone 2mg QD', 'include_sensitivity':True})
    assert response.status_code==200
    assert load_workbook(io.BytesIO(response.data)).sheetnames == OLD_SHEETS
