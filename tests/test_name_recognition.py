"""2026-10-29: recognize as many drug names as possible without AI, and read a-b-c regimens."""
import pytest
from app import app


def item(text):
    return app.test_client().post('/api/parse', json={'text': text}).json['items'][0]


@pytest.mark.parametrize('text,daily,basis', [
    ('risperidone2 0.5-0-1', 1.5, '약물명 뒤 숫자(2)'),
    ('리스페리돈2 0.5-0-1', 1.5, '약물명 뒤 숫자(2)'),
    ('risperidone 0.5-0-1', 1.5, '함량(mg) 기재 없음'),
    ('risperidone 2mg 0.5-0-1', 3, '정 수'),
    ('risperidone2mg 0.5-0-1', 3, '정 수'),
])
def test_abc_regimen_basis(text, daily, basis):
    result = item(text)
    assert result['drug'] == 'risperidone' and result['daily_dose_mg'] == daily
    assert basis in result['regimen_basis'] and basis in result['calculation_note']


def test_abc_mg_reading_is_flagged_but_tablet_reading_is_standard():
    assert 'c' in item('risperidone2 0.5-0-1')['status_code'].split(';')
    assert not item('risperidone 2mg 0.5-0-1').get('regimen_mg_assumed')
    assert item('risperidone 2 0.5-0-1')['daily_dose_mg'] == 1.5


@pytest.mark.parametrize('text,drug', [
    ('奥氮平 10mg', 'olanzapine'), ('奧氮平 10mg', 'olanzapine'), ('利培酮 2mg', 'risperidone'),
    ('オランザピン 10mg', 'olanzapine'), ('クエチアピン100mg', 'quetiapine'), ('рисперидон 2mg', 'risperidone'),
    ('olanzapina 10mg', 'olanzapine'), ('Quetiapin 100mg', 'quetiapine'), ('rispéridone 2mg', 'risperidone'),
    ('olanzapinum 5mg', 'olanzapine'), ('Qrokel 25mg', 'quetiapine'), ('Rispen 2mg', 'risperidone'),
    ('Lonasen 8mg', 'blonanserin'), ('Invega Sustenna 150mg', 'paliperidone'),
])
def test_multilingual_and_brand_names(text, drug):
    assert item(text)['drug'] == drug


@pytest.mark.parametrize('text,drug', [
    ('Ativan 1mg', 'lorazepam'), ('Slivan 1mg', 'lorazepam'), ('Indenol 40mg', 'propranolol'),
    ('Xanax 0.5mg', 'alprazolam'), ('Depakote 500mg', 'valproate'), ('舍曲林 50mg', 'sertraline'),
    ('лоразепам 1mg', 'lorazepam'), ('스틸녹스정 10mg', 'zolpidem'),
])
def test_non_antipsychotic_names_contribute_zero(text, drug):
    result = item(text)
    assert result['drug'] == drug and result['status'] == 'non_target'


@pytest.mark.parametrize('text,drug,word', [
    ('rispiridone 2mg BID', 'risperidone', 'rispiridone'), ('abilfy 15mg QD', 'aripiprazole', 'abilfy'),
    ('olanzepine 10mg', 'olanzapine', 'olanzepine'), ('Benzotropine 1mg', 'benztropine', 'Benzotropine'),
    ('올란자팬 10mg', 'olanzapine', '올란자팬'), ('아리피프라즐 10mg', 'aripiprazole', '아리피프라즐'),
    ('quetia 100mg', 'quetiapine', 'quetia'),
])
def test_unique_typo_is_corrected_without_ai_and_flagged(text, drug, word):
    result = item(text)
    assert result['drug'] == drug and result['match_type'] == 'spelling_corrected'
    assert result['spelling_correction'].startswith(word) and 'AI 미사용' in result['warning']
    assert 'c' in result['status_code'].split(';')


@pytest.mark.parametrize('text', ['zzqxv 5mg', 'Tepraxx 60mg'])
def test_unlisted_name_far_from_antipsychotics_counts_zero_with_flag(text):
    data = app.test_client().post('/api/parse', json={'text': text}).json
    result = data['items'][0]
    assert result['status'] == 'non_target' and result['unlisted'] and 'c' in result['status_code'].split(';')
    assert '사전 외 약물' in result['warning'] and data['cases'][0]['total'] == 0


@pytest.mark.parametrize('text', ['neurozapine 1mg', 'qtpxx 5mg', 'lonaserine 4mg', 'unknownzapine 5mg LAI'])
def test_names_close_to_antipsychotics_stay_held(text):
    assert item(text)['status'] == 'unknown_drug'


@pytest.mark.parametrize('text,drug,product', [('Qrokel 25mg', 'quetiapine', '큐로켈'), ('Slivan 1mg', 'lorazepam', '스리반'),
                                               ('Indenol 40mg', 'propranolol', '인데놀'),
                                               # Two Latin words for one product; 'proma' alone must not become promazine.
                                               ('Young proma 5mg', 'procyclidine', '영프로마'),
                                               ('youngproma 10mg', 'procyclidine', '영프로마')])
def test_romanized_korean_product_names(text, drug, product):
    result = item(text)
    assert result['drug'] == drug and result['correction_kind'] == 'romanized_product' and product in result['warning']


@pytest.mark.parametrize('text,drug', [('아티반정 1mg', 'lorazepam'), ('큐로켈정 100mg', 'quetiapine'), ('cariprazine 3mg', 'cariprazine')])
def test_public_product_and_unfactored_antipsychotic_names(text, drug):
    assert item(text)['drug'] == drug


def test_dictionary_build_never_uses_validation_data():
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[1] / 'lookup/external_names.json').read_text(encoding='utf-8'))
    assert 'never used' in data['policy'] and set(data['sources']) == {'wikidata', 'rxnorm', 'khidi'}
    supplement = json.loads((Path(__file__).resolve().parents[1] / 'lookup/name_supplement.json').read_text(encoding='utf-8'))
    assert not any('전북대' in e.get('seen_in', '') or '서울대' in e.get('seen_in', '') or '부산대' in e.get('seen_in', '')
                   for e in supplement['entries'])


def test_unclosed_note_bracket_does_not_hold_the_cell():
    data = app.test_client().post('/api/parse', json={'text': 'CPZ200mg,Seroquel200mg(2009 본원 처방(확인 안됨) 저녁 1회'}).json
    assert [(i['drug'], i['daily_dose_mg']) for i in data['items']] == [('chlorpromazine', 200), ('quetiapine', 200)]
    assert all('괄호 짝' in i['warning'] for i in data['items'])


@pytest.mark.parametrize('text', ['P001\trisperidone 2mg bid', '환자ID\t약물\nP001\trisperidone 2mg bid', '12345\trisperidone 2mg bid'])
def test_pasted_patient_id_cell_is_not_a_drug(text):
    items = app.test_client().post('/api/parse', json={'text': text}).json['items']
    assert [(i['drug'], i['daily_dose_mg']) for i in items] == [('risperidone', 4)]


def test_drug_abbreviation_in_first_cell_is_kept():
    assert item('olz10\tqd')['drug'] == 'olanzapine'


def test_result_file_lists_unlisted_names():
    import io
    import pandas as pd
    source = io.BytesIO()
    pd.DataFrame({'환자ID': ['P1', 'P2', 'P2'], '약물': ['Zorbex 10mg', 'Zorbex 5mg', 'olanzapine 5mg']}).to_excel(source, index=False)
    source.seek(0)
    response = app.test_client().post('/upload', data={'file': (source, 'input.xlsx')}, content_type='multipart/form-data')
    sheet = pd.read_excel(io.BytesIO(response.data), sheet_name='UnlistedNames')
    assert sheet.iloc[0].tolist()[:3] == ['Zorbex', 2, 2]
