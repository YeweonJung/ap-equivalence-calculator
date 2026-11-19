import datetime
import io
import json

import pandas as pd
import pytest

from app import app
from services.longitudinal import parse_date

MAPPING = {'patient': 'HID', 'date': 'PRESCR_DATE', 'drug': 'DRUG', 'product': '', 'code': '', 'daily': 'TABS_PER_DAY', 'days': 'PRESCR_DAYS'}


@pytest.mark.parametrize('value', ['2024-01-02', '20240102', '2024.01.02', '2024/1/2', '2024-01-02 00:00:00', '2024-01-02 09:30',
                                   '2024-01-02T09:30:00', '2024년 1월 2일', '45293', datetime.datetime(2024, 1, 2, 9, 30), pd.Timestamp('2024-01-02')])
def test_prescription_dates_from_excel_and_emr_exports(value):
    assert parse_date(value) == datetime.date(2024, 1, 2)


@pytest.mark.parametrize('value', ['24-01-02', '2024-13-01', 'yesterday', '12345'])
def test_unreadable_dates_are_rejected(value):
    with pytest.raises(ValueError):
        parse_date(value)


def _analyze(frame, name='rx.xlsx'):
    raw = io.BytesIO()
    frame.to_excel(raw, index=False) if name.endswith('.xlsx') else raw.write(frame.to_csv(index=False).encode())
    return app.test_client().post('/api/longitudinal/analyze', data={'file': (io.BytesIO(raw.getvalue()), name),
        'mapping': json.dumps(MAPPING), 'ack': 'yes', 'mode': 'all_dates', 'base_method': 'ED95'})


def test_excel_date_cells_are_read_on_the_hospital_data_page():
    frame = pd.DataFrame({'HID': ['P1'], 'PRESCR_DATE': [datetime.datetime(2024, 1, 2)], 'DRUG': ['olanzapine 10mg tab'], 'TABS_PER_DAY': [2], 'PRESCR_DAYS': [7]})
    response = _analyze(frame)
    assert response.status_code == 200
    results = pd.read_excel(io.BytesIO(response.data), sheet_name='Results')
    assert str(results['처방일'][0]).startswith('2024-01-02')


def test_no_readable_date_names_an_example():
    frame = pd.DataFrame({'HID': ['P1'], 'PRESCR_DATE': ['24-01-02'], 'DRUG': ['olanzapine 10mg tab'], 'TABS_PER_DAY': [2], 'PRESCR_DAYS': [7]})
    response = _analyze(frame, 'rx.csv')
    assert response.status_code == 400
    assert "'24-01-02'" in response.get_json()['error'] and '연도 네 자리' in response.get_json()['error']


def test_main_upload_stops_above_1000_rows():
    frame = pd.DataFrame({'id': [f'P{i}' for i in range(1001)], 'med': ['olanzapine 5mg'] * 1001})
    raw = io.BytesIO(); frame.to_excel(raw, index=False); raw.seek(0)
    response = app.test_client().post('/upload', data={'file': (raw, 'big.xlsx'), 'dated': 'page'})
    assert response.status_code == 400 and '1,000행까지' in response.get_data(as_text=True)


def test_hospital_data_page_stops_above_2000_rows():
    frame = pd.DataFrame({'HID': ['P1'] * 2001, 'PRESCR_DATE': ['2024-01-02'] * 2001, 'DRUG': ['olanzapine 10mg tab'] * 2001, 'TABS_PER_DAY': [1] * 2001, 'PRESCR_DAYS': [7] * 2001})
    response = app.test_client().post('/api/longitudinal/inspect', data={'file': (io.BytesIO(frame.to_csv(index=False).encode()), 'rx.csv')})
    assert response.status_code == 400 and '2,000행까지' in response.get_json()['error']


def test_sources_page_has_no_internal_metadata_label():
    page = app.test_client().get('/methods').get_data(as_text=True)
    assert 'evidence-1' not in page and '근거 메타데이터' not in page
    assert '교체 처방·최적 용량 지침이 아닙니다' in page
