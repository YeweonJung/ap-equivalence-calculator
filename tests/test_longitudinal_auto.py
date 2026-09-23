import csv
import io
import zipfile
from datetime import datetime

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from app import app
from services.longitudinal_auto import automatic_analysis
from tests.test_longitudinal import rx


def entries(buffer, name='Results'):
    wb = load_workbook(buffer, read_only=True)
    rows = wb[name].values
    headers = next(rows)
    output = [dict(zip(headers, row)) for row in rows]
    wb.close()
    return output


def test_automatic_reference_dates_from_rows():
    frame = pd.DataFrame([rx(), rx('2020-04-26', tabs='1')])
    results = entries(automatic_analysis({'SNU':frame}, ['DDD']))
    assert {r['처방일'] for r in results} == {'2020-04-15', '2020-04-26'}
    assert [r['결과 상태'] for r in results] == ['계산 완료', '계산 완료']
    assert results[1]['DDD (CPZ mg/day)'] == pytest.approx(results[0]['DDD (CPZ mg/day)'] * 2)
    assert all(r['기준일 선택'] == '각 처방일' for r in results)


def test_reference_columns_do_not_override_prescription_dates():
    rows = [dict(rx(), reference_date='2020-04-20'), dict(rx('2020-04-26'), reference_date=''), dict(rx(patient='P002'), reference_date='')]
    result = entries(automatic_analysis({'Data':pd.DataFrame(rows)}, ['DDD']))
    assert [(r['patient_id'],r['처방일'],r['기준일 선택']) for r in result] == [('P001','2020-04-15','각 처방일'),('P001','2020-04-26','각 처방일'),('P002','2020-04-15','각 처방일')]


def test_multiple_reference_columns_are_ignored():
    result = entries(automatic_analysis({'Data':pd.DataFrame([dict(rx(), baseline_date='2020-04-20', mri_date='2020-04-21')])}, ['DDD']))
    assert result[0]['처방일'] == '2020-04-15'


def test_excel_native_dates_multiple_sheets_via_main_upload():
    wb = Workbook()
    a = wb.active; a.title = 'Earlier'
    columns = list(rx())
    a.append(columns)
    a.append(list(rx(day=datetime(2020,4,15)).values()))
    b = wb.create_sheet('Later'); b.append(columns)
    b.append(list(rx(day=datetime(2020,4,26), tabs='1').values()))
    content = io.BytesIO(); wb.save(content); content.seek(0)
    response = app.test_client().post('/upload', data={'file':(content,'synthetic.xlsx'),'method':'DDD'})
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    results = entries(io.BytesIO(response.data))
    assert len(results) == 2
    detail = entries(io.BytesIO(response.data), 'MedicationResults')
    assert {(r['원본 시트'], r['원본 행']) for r in detail if r['처방일'] == '2020-04-26'} == {('Later', 2)}


def test_mixed_static_and_longitudinal_sheets_fail_closed():
    with pytest.raises(ValueError, match='필수 열'):
        automatic_analysis({'Rx':pd.DataFrame([rx()]),'Static':pd.DataFrame([dict(patient_id='P1',drug='risperidone 2mg')])}, ['DDD'])


def test_invalid_prescription_dates_cannot_be_replaced_by_reference_date():
    with pytest.raises(ValueError, match='유효한'):
        automatic_analysis({'Data':pd.DataFrame([dict(rx(day='unknown'), reference_date='2020-04-20')])}, ['DDD'])


def test_main_one_line_unchanged():
    response = app.test_client().post('/api/parse', json={'text':'risperidone 2mg QD'})
    assert response.status_code == 200
    assert response.json['items'][0]['daily_dose_mg'] == 2


def test_main_csv_blank_rows_keep_original_row_numbers():
    raw = pd.DataFrame([rx(), rx('2020-04-26')]).to_csv(index=False).replace('\n', '\n\n', 1).encode()
    response = app.test_client().post('/upload', data={'file':(io.BytesIO(raw),'synthetic.csv')})
    assert response.status_code == 200
    assert {r['원본 행'] for r in entries(io.BytesIO(response.data),'MedicationResults')} == {3,4}


def test_exact_date_sums_same_ingredient_strengths_and_separates_patients():
    from services.converter import convert_drug
    frame = pd.DataFrame([
        rx(patient='001', tabs='1'),
        rx(patient='001', drug='Quetiapine 100mg tab', tabs='1'),
        rx(patient='001', day='2020-04-16', drug='Risperidone 2mg tab', tabs='1'),
        rx(patient='002', tabs='2'),
    ])
    result = entries(automatic_analysis({'Data':frame}, ['DDD']))
    totals = {(r['patient_id'], r['처방일']):r['DDD (CPZ mg/day)'] for r in result}
    assert len(totals) == 3
    assert totals['001','2020-04-15'] == pytest.approx(convert_drug('quetiapine',125,method='DDD'))
    assert totals['001','2020-04-16'] == pytest.approx(convert_drug('risperidone',2,method='DDD'))
    assert totals['002','2020-04-15'] == pytest.approx(convert_drug('quetiapine',50,method='DDD'))


@pytest.mark.parametrize('days', ['', '0', '-1', 'invalid', '99999999'])
def test_duration_does_not_affect_exact_date_totals(days):
    result = entries(automatic_analysis({'Data':pd.DataFrame([rx(days=days)])}, ['DDD']))
    assert result[0]['결과 상태'] == '계산 완료'


def test_missing_days_column_supported_on_main_and_detail_api():
    raw = pd.DataFrame([rx(),rx('2020-04-26')]).drop(columns=['PRESCR_DAYS']).to_csv(index=False).encode()
    for route in ['/upload','/api/longitudinal/analyze']:
        response = app.test_client().post(route, data={'file':(io.BytesIO(raw),'synthetic.csv'), 'ack':'yes', 'policy':'replace'})
        assert response.status_code == 200
        result = entries(io.BytesIO(response.data))
        assert {r['처방일'] for r in result} == {'2020-04-15','2020-04-26'}
        assert all(r['DDD (CPZ mg/day)'] is not None for r in result)


def test_duplicates_and_unknown_drug_still_block_only_their_date():
    result = entries(automatic_analysis({'Data':pd.DataFrame([
        rx(),rx(),rx('2020-04-16'),rx('2020-04-17',drug='unknown 5mg tab')])}, ['DDD']))
    assert [r['결과 상태'] for r in result] == ['확인 필요','계산 완료','확인 필요']


def test_same_patient_date_merges_across_sheets():
    from services.converter import convert_drug
    result = entries(automatic_analysis({'A':pd.DataFrame([rx(tabs='1')]),'B':pd.DataFrame([rx(drug='Quetiapine 100mg tab',tabs='1')])},['DDD']))
    assert len(result) == 1
    assert result[0]['DDD (CPZ mg/day)'] == pytest.approx(convert_drug('quetiapine',125,method='DDD'))
