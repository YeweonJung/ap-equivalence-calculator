import io

import pandas as pd
import pytest

from app import app
from services.frames import parse_frames
from services.medication_splitter import split_medications
from services.parser import parse_medication


def items(text):
    response = app.test_client().post('/api/parse', json={'text': text})
    assert response.status_code == 200
    return response.get_json()['items']


def test_annotations_remain_attached_and_offsets_are_original():
    text = '  Risperidone 2mg (tablet, 경구); olz 5mg (경구 [정제, 설명])'
    assert len(split_medications(text)) == 2
    frames = parse_frames(text)
    assert len(frames) == 2
    for frame in frames:
        assert text[frame['source_start']:frame['source_end']] == frame['original']
    assert [x['drug'] for x in frames] == ['risperidone', 'olanzapine']


@pytest.mark.parametrize('text', ['ris 2mg (경구', 'ris 2mg 경구)', 'ris 2mg ([)]'])
def test_unbalanced_annotations_remain_reviewable(text):
    result = items(text)
    assert len(result) == 1 and result[0]['status'] == 'review'
    assert result[0]['original'] == text


def test_drug_dose_binding_and_unknown_neighbors():
    result = items('ris 2mg olz 5')
    assert [(r['drug'], r['dose'], r['status']) for r in result] == [
        ('risperidone', 2, 'converted'), ('olanzapine', 5, 'converted')]
    result = items('ris 2mg UnknownDrug 7mg olz 5mg')
    assert [r['status'] for r in result] == ['converted', 'unknown_drug', 'converted']
    with pytest.raises(ValueError):
        parse_medication('ris 2mg olz 5')


@pytest.mark.parametrize('marker', ['PP1M', 'PP3M', 'PP6M', 'LAI', 'IM', '주사'])
def test_injections_never_become_oral_daily_doses(marker):
    result = items(f'Paliperidone 100mg ({marker})')[0]
    assert result['route'] == 'injection'
    if marker.startswith('PP'):
        assert result['status'] == 'converted' and result['daily_dose_mg'] < 100
        assert [c['method'] for c in result['conversions'] if c['value'] is not None] == ['DDD']
    else:
        assert result['status'] == 'unsupported_formulation'
        assert result['dose_mg'] == 100 and result['daily_dose_mg'] is None
        assert result['conversions'] == []


def test_non_targets_and_missing_factors_are_distinct():
    result = items('Escitalopram 10mg, Benztropine 1mg, Lithium 600mg, Blonanserin 8mg')
    assert [r['status'] for r in result] == ['non_target'] * 3 + ['missing_factor']
    assert all(not any(c['value'] is not None for c in r['conversions']) for r in result)


@pytest.mark.parametrize('text,drug', [('arp 15', 'aripiprazole'), ('hd 1.5', 'haloperidol'),
    ('olz15', 'olanzapine'), ('olan 7.5', 'olanzapine'), ('ris 6', 'risperidone'), ('qtp 300', 'quetiapine')])
def test_aliases_use_requested_mg_default_with_review(text, drug):
    result = items(text)[0]
    assert result['drug'] == drug and result['status'] == 'converted'
    assert result['unit'] == 'mg' and result['unit_assumed'] and result['needs_review']
    assert '확인바람' in result['warning']


def test_unit_normalization_and_ambiguous_typo():
    assert items('olz15mg')[0]['dose_mg'] == 15
    assert items('olz 15mgs')[0]['dose_mg'] == 15
    assert items('olz 15gm')[0]['status'] == 'missing_unit'
    assert items('pariperidon 6mg')[0]['drug'] == 'paliperidone'


def test_excel_retains_all_statuses_and_numbered_groups():
    content = 'patient_id,drug1,dose1,unit1,drug2,dose2,unit2\nP1,ris,2,mg,lithium,600,mg\nP2,olz,5,mg,Blonanserin,8,mg\n'
    response = app.test_client().post('/upload', data={'method': 'ALL', 'file': (io.BytesIO(content.encode()), 'groups.csv')})
    assert response.status_code == 200
    sheets = pd.read_excel(io.BytesIO(response.data), sheet_name=None)
    assert sheets['AuditTrail']['status'].tolist() == ['converted', 'non_target', 'converted', 'missing_factor']
    assert set(sheets['Detailed']['drug']) == {'risperidone', 'olanzapine'}
    assert 'method_warning' not in sheets['Detailed']
    assert 'limitation' not in sheets['MethodInfo']


def test_invalid_schedule_does_not_create_a_second_drug():
    result = items('risperidone 1mg AM 2mg PM')
    assert len(result) == 1 and result[0]['status'] == 'review'


def test_unbracketed_pp1m_and_annotation_do_not_change_drug_binding():
    result = items('Paliperidone 100mg PP1M')
    assert len(result) == 1 and result[0]['status'] == 'converted'
    result = items('ris 2mg (previous olanzapine)')[0]
    assert result['drug'] == 'risperidone'


def test_unit_typo_candidates_are_not_conversion_factors():
    result = items('olz 15gm')[0]
    assert result['unit'] == 'gm' and result['unit_candidates']
    assert result['daily_dose_mg'] is None and result['conversions'] == []


def test_cell_totals_complete_partial_and_absent_doses():
    for text, complete in [('RIS 2mg, OLZ 5mg', True), ('RIS 2mg, OLZ', False), ('RIS,OLZ', False)]:
        data = app.test_client().post('/api/parse', json={'text': text}).get_json()
        total = next(t for t in data['totals'] if t['method'] == 'CMD')
        assert (total['status'] == 'complete') is complete
        if complete:
            from services.converter import convert_drug
            assert total['total_equivalent_dose_mg'] == round(convert_drug('risperidone', 2) + convert_drug('olanzapine', 5), 4)
        else:
            assert total['total_equivalent_dose_mg'] is None
    data = app.test_client().post('/api/parse', json={'text': 'RIS 2mg, lithium 600mg'}).get_json()
    total = next(t for t in data['totals'] if t['method'] == 'CMD')
    assert total['status'] == 'complete' and total['excluded_count'] == 1


def test_excel_totals_stay_with_source_cell():
    csv = 'patient_id,medication\nP1,"RIS 2mg, OLZ 5mg"\nP1,"RIS, OLZ"\n'
    response = app.test_client().post('/upload', data={'method':'CMD','file':(io.BytesIO(csv.encode()),'totals.csv')})
    sheets = pd.read_excel(io.BytesIO(response.data), sheet_name=None)
    assert len(sheets['Detailed']) == 2
    totals = sheets['CellTotals']
    assert totals['status'].tolist() == ['complete', 'incomplete']
    assert pd.isna(totals.loc[1, 'total_equivalent_dose_mg'])


def test_parallel_drug_dose_columns_and_frequency_validation():
    for frequency, status in [('BID', 'complete'), ('B', 'incomplete')]:
        csv = f'patient_id,drug,dose,unit,frequency\nP003,"Risperdal,OLA","6,5",MG,{frequency}\n'
        response = app.test_client().post('/upload', data={'method':'CMD','file':(io.BytesIO(csv.encode()),'parallel.csv')})
        sheets = pd.read_excel(io.BytesIO(response.data), sheet_name=None)
        assert sheets['AuditTrail']['dose_mg'].tolist() == [6,5]
        assert sheets['CellTotals'].loc[0,'status'] == status
        if frequency == 'BID':
            assert sheets['Detailed']['daily_dose_mg'].tolist() == [12,10]
        else:
            assert sheets['Detailed'].empty


def test_parallel_counts_do_not_broadcast_one_dose_to_two_drugs():
    csv = 'patient_id,drug,dose,unit,frequency\nP1,"RIS,OLZ",2,mg,BID\n'
    response = app.test_client().post('/upload', data={'method':'CMD','file':(io.BytesIO(csv.encode()),'mismatch.csv')})
    sheets = pd.read_excel(io.BytesIO(response.data), sheet_name=None)
    assert sheets['Detailed'].empty
    assert sheets['CellTotals'].loc[0,'status'] == 'incomplete'
