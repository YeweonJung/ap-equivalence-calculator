"""By-date page: Excel input and matching by insurance (EDI) product code (2026-11-19)."""
import io
import json

import pandas as pd
from openpyxl import load_workbook

from app import app
from services.korean_products import product_by_code, CATALOG

ORAL = next(p for p in CATALOG['products'] if p['drug'] == 'olanzapine' and p['route'] == '내복' and p['dose_mg'] == 10)


def xlsx(frame, extra=None):
    book = io.BytesIO()
    with pd.ExcelWriter(book, engine='openpyxl') as writer:
        frame.to_excel(writer, sheet_name='rx', index=False)
        if extra is not None:
            extra.to_excel(writer, sheet_name='memo', index=False)
    return book.getvalue()


def post(path, data, name, **fields):
    return app.test_client().post(path, data={'file': (io.BytesIO(data), name), **fields})


EMR = pd.DataFrame({'환자번호': ['P1', 'P1'], '처방일': ['2026-01-02', '2026-01-02'],
                    '약품코드': [ORAL['code'], '999999999'], '약품명': ['처방명 기록 오류', 'lorazepam 1mg tab'],
                    '1일정수': ['2', '1'], '일수': ['28', '28']})
MAPPING = {'patient': '환자번호', 'date': '처방일', 'drug': '약품명', 'daily': '1일정수', 'days': '일수', 'code': '약품코드', 'product': ''}


def test_code_lookup_tolerates_spaces_and_excel_numbers():
    assert product_by_code(' ' + ORAL['code'] + ' ')['drug'] == 'olanzapine'
    assert product_by_code(ORAL['code'] + '.0')['drug'] == 'olanzapine'
    assert product_by_code('') is None and product_by_code('abc') is None


def test_inspect_reads_excel_and_lists_columns():
    response = post('/api/longitudinal/inspect', xlsx(EMR), 'emr.xlsx')
    assert response.status_code == 200
    data = response.get_json()
    assert data['columns'] == list(EMR.columns)
    assert data['mapping']['code'] == '약품코드'


def test_excel_with_two_filled_sheets_is_refused():
    response = post('/api/longitudinal/inspect', xlsx(EMR, pd.DataFrame({'a': [1]})), 'emr.xlsx')
    assert response.status_code == 400 and '시트 하나만' in response.get_json()['error']


def audit(response):
    rows = list(load_workbook(io.BytesIO(response.data), read_only=True)['AuditTrail'].values)
    return [dict(zip(rows[0], row)) for row in rows[1:]]


def test_code_fixes_ingredient_and_strength_and_unknown_code_falls_back_to_name():
    response = post('/api/longitudinal/analyze', xlsx(EMR), 'emr.xlsx', mapping=json.dumps(MAPPING), ack='yes', mode='all_dates')
    assert response.status_code == 200, response.get_data(as_text=True)[:300]
    olz, lorazepam = audit(response)
    assert (olz['canonical'], olz['strength_mg'], olz['daily_mg']) == ('olanzapine', 10, 20)
    assert olz['adjustments'] == 'matched_by_insurance_code' and olz['insurance_code'] == ORAL['code']
    assert lorazepam['canonical'] == 'lorazepam' and lorazepam['adjustments'] == 'insurance_code_not_in_antipsychotic_catalogue'


def test_code_and_name_for_different_ingredients_is_held():
    frame = EMR.iloc[:1].copy()
    frame['약품명'] = 'risperidone 2mg tab'
    response = post('/api/longitudinal/analyze', xlsx(frame), 'emr.xlsx', mapping=json.dumps(MAPPING), ack='yes', mode='all_dates')
    assert response.status_code == 200
    row = audit(response)[0]
    assert row['상태코드'] == 'x' and 'code_name_conflict' in row['issues']


def test_without_a_code_column_names_are_read_as_before():
    mapping = dict(MAPPING, code='')
    frame = EMR.drop(columns=['약품코드']).iloc[1:]
    response = post('/api/longitudinal/analyze', xlsx(frame), 'emr.xlsx', mapping=json.dumps(mapping), ack='yes', mode='all_dates')
    assert response.status_code == 200 and audit(response)[0]['canonical'] == 'lorazepam'
