"""Files as hospital record systems export them must never fail without a clear, fixable message."""
import datetime
import io
import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from app import app

FIX = Path(__file__).parent / 'fixtures' / 'emr'
COLUMNS = ['등록번호', '처방 일자', '보험코드', '약품명', '1회량', '횟수', '총량', '일수']
MAPPING = {'patient': '등록번호', 'date': '처방 일자', 'drug': '약품명', 'product': '', 'code': '보험코드', 'daily': '총량', 'days': '일수'}


def title_rows_xlsx():
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = '처방조회'
    ws['A1'] = '외래 처방 내역 조회'; ws.merge_cells('A1:H1'); ws['A2'] = '조회기간: 2024-01-01 ~ 2024-01-31'; ws.append([])
    header = ['등록번호', '처방\n일자', '보험코드', '약품명', '1회량', '횟수', '총량', '일수']
    ws.append(header)
    ws.append([1001, datetime.datetime(2024, 1, 2, 9, 30), 657202160, '자이프렉사정10mg', 1, 2, '2정', 7])
    ws.append([1001, datetime.datetime(2024, 1, 2, 9, 30), None, '로라제팜정1mg', 1, 1, 1, 7])
    ws.append([2002, datetime.datetime(2024, 1, 3), None, '리스페달정 2mg', 1, 2, 2, 14])
    ws.append(header)
    ws.append([2002, datetime.datetime(2024, 1, 10), None, 'Seroquel 100mg tab', 1, 1, '1T', 7])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def html_table():
    rows = [COLUMNS, ['1001', '2024-01-02 오전 9:30:00', '657202160', '자이프렉사정10mg', '1', '2', '2', '7'],
            ['2002', '2024. 1. 3.', '', '리스페달정 2mg', '1', '2', '2', '14']]
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<html><head><meta charset="euc-kr"></head><body><table border=1>{body}</table></body></html>'.encode('cp949')


def utf16_tab():
    return ('\t'.join(COLUMNS) + '\r\n' + '1001\t2024-01-02\t657202160\t자이프렉사정10mg\t1\t2\t2\t7\r\n').encode('utf-16')


FILES = {
    'title_rows.xlsx': title_rows_xlsx,
    'excel97.xls': lambda: (FIX / 'excel97.xls').read_bytes(),
    'excel_unicode_text.xls': lambda: (FIX / 'excel_unicode_text.xls').read_bytes(),
    'excel_cp949.csv': lambda: (FIX / 'excel_cp949_csv.dat').read_bytes(),
    'webpage.xls': html_table,
    'utf16.txt': utf16_tab,
}


@pytest.mark.parametrize('name', FILES)
def test_hospital_exports_are_read_and_calculated(name):
    raw = FILES[name](); client = app.test_client()
    data = client.post('/api/longitudinal/inspect', data={'file': (io.BytesIO(raw), name)}).get_json()
    assert data['columns'] == COLUMNS, data
    assert data['mapping']['patient'] == '등록번호' and data['mapping']['drug'] == '약품명'
    response = client.post('/api/longitudinal/analyze', data={'file': (io.BytesIO(raw), name), 'mapping': json.dumps(MAPPING), 'ack': 'yes', 'mode': 'all_dates', 'base_method': 'ED95'})
    assert response.status_code == 200, response.get_json()
    results = pd.read_excel(io.BytesIO(response.data), sheet_name='Results')
    first = results.iloc[0]
    assert str(first['환자 ID']) == '1001' and str(first['처방일']).startswith('2024-01-02')
    assert float(first.filter(like='ED95').iloc[0]) == 20.0   # olanzapine 10 mg by insurance code, 2 tablets


def test_original_row_numbers_survive_title_and_repeated_header_rows():
    raw = title_rows_xlsx()
    response = app.test_client().post('/api/longitudinal/analyze', data={'file': (io.BytesIO(raw), 'x.xlsx'), 'mapping': json.dumps(MAPPING), 'ack': 'yes', 'mode': 'all_dates'})
    audit = pd.read_excel(io.BytesIO(response.data), sheet_name='AuditTrail')
    assert list(audit['source_row']) == [5, 6, 7, 9]


@pytest.mark.parametrize('name, raw, words', [
    ('password.xlsx', (FIX / 'password_1234.xlsx').read_bytes(), '암호'),
    ('empty.csv', b'', '빈 파일'),
    ('scan.xlsx', b'%PDF-1.4', 'PDF'),
    ('header_only.csv', 'a,b,c\n'.encode(), '처방 줄'),
    ('narrow.xls', (FIX / 'excel_webpage.xls').read_bytes(), None),
])
def test_unreadable_files_get_a_fixable_message(name, raw, words):
    client = app.test_client()
    response = client.post('/api/longitudinal/inspect', data={'file': (io.BytesIO(raw), name)})
    if words is None:   # Excel web page with '#####' in a narrow date column
        assert response.status_code == 200
        response = client.post('/api/longitudinal/analyze', data={'file': (io.BytesIO(raw), name), 'mapping': json.dumps(MAPPING), 'ack': 'yes', 'mode': 'all_dates'})
        assert response.status_code == 400 and '너비' in response.get_json()['error']
        return
    assert response.status_code == 400 and words in response.get_json()['error']


@pytest.mark.parametrize('name, raw', [
    ('utf16.csv', 'id\tmed\nP1\tolanzapine 5mg\n'.encode('utf-16')),
    ('table.xls', '<table><tr><td>id</td><td>med</td></tr><tr><td>P1</td><td>olanzapine 5mg</td></tr></table>'.encode('cp949')),
])
def test_researcher_files_in_odd_formats_work_on_the_excel_page(name, raw):
    response = app.test_client().post('/upload', data={'file': (io.BytesIO(raw), name), 'dated': 'page'})
    assert response.status_code == 200


@pytest.mark.parametrize('name, raw, words', [
    ('password.xlsx', (FIX / 'password_1234.xlsx').read_bytes(), '암호'),
    ('scan.pdf', b'%PDF-1.4', 'CSV 또는 Excel'),
    ('emr.csv', 'ORD_DT,PT_NO,ORD_NM\n2024-01-02,1,olanzapine\n'.encode(), '전산실 처방자료 분석'),
])
def test_excel_page_never_shows_a_server_error(name, raw, words):
    response = app.test_client().post('/upload', data={'file': (io.BytesIO(raw), name), 'dated': 'page'})
    assert response.status_code == 400 and words in response.get_data(as_text=True)


def test_hospital_exports_from_excel_land_on_the_linking_page():
    response = app.test_client().post('/upload', data={'file': (io.BytesIO((FIX / 'excel_unicode_text.xls').read_bytes()), 'x.xls'), 'dated': 'page'})
    assert response.status_code == 409 and response.get_json()['redirect'] == '/longitudinal?from=upload'


@pytest.mark.parametrize('value, expected', [('2', 2), ('2정', 2), ('1T', 1), ('0.5 tab', 0.5), ('1/2', 0.5), ('½', 0.5), ('7일', 7), ('20mg', None), ('1-0-1', None), ('0', None)])
def test_tablet_and_day_counts(value, expected):
    from services.longitudinal import number
    assert number(value) == expected


@pytest.mark.parametrize('value', ['2024. 1. 2.', '2024-01-02 오전 9:30:00', '2024-01-02(화)', '2024/1/2 13:00', '45293.395833'])
def test_korean_and_timestamp_dates(value):
    from services.longitudinal import parse_date
    assert parse_date(value) == datetime.date(2024, 1, 2)
