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
        ('risperidone', 2, 'converted'), ('olanzapine', 5, 'missing_unit')]
    result = items('ris 2mg UnknownDrug 7mg olz 5mg')
    assert [r['status'] for r in result] == ['converted', 'unknown_drug', 'converted']
    with pytest.raises(ValueError):
        parse_medication('ris 2mg olz 5')


@pytest.mark.parametrize('marker', ['PP1M', 'PP3M', 'PP6M', 'LAI', 'IM', '주사'])
def test_injections_never_become_oral_daily_doses(marker):
    result = items(f'Paliperidone 100mg ({marker})')[0]
    assert result['route'] == 'injection'
    assert result['status'] == 'unsupported_formulation'
    assert result['dose_mg'] == 100 and result['daily_dose_mg'] is None
    assert result['conversions'] == []


def test_non_targets_and_missing_factors_are_distinct():
    result = items('Escitalopram 10mg, Benztropine 1mg, Lithium 600mg, Blonanserin 8mg')
    assert [r['status'] for r in result] == ['non_target'] * 3 + ['missing_factor']
    assert all(not any(c['value'] is not None for c in r['conversions']) for r in result)


@pytest.mark.parametrize('text,drug', [('arp 15', 'aripiprazole'), ('hd 1.5', 'haloperidol'),
    ('olz15', 'olanzapine'), ('olan 7.5', 'olanzapine'), ('ris 6', 'risperidone'), ('qtp 300', 'quetiapine')])
def test_aliases_recognized_without_inventing_units(text, drug):
    result = items(text)[0]
    assert result['drug'] == drug and result['status'] == 'missing_unit'
    assert result['unit'] is None and result['daily_dose_mg'] is None


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
    assert len(result) == 1 and result[0]['status'] == 'unsupported_formulation'
    result = items('ris 2mg (previous olanzapine)')[0]
    assert result['drug'] == 'risperidone'


def test_unit_typo_candidates_are_not_conversion_factors():
    result = items('olz 15gm')[0]
    assert result['unit'] == 'gm' and result['unit_candidates']
    assert result['daily_dose_mg'] is None and result['conversions'] == []
