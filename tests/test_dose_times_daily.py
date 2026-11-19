"""Hospital exports without a tablets-per-day column: tablets per dose x doses per day."""
import io
import json

import pandas as pd

from app import app

BASE = {'patient': 'HID', 'date': 'PRESCR_DATE', 'drug': 'DRUG', 'product': '', 'code': '', 'days': ''}


def analyze(rows, mapping):
    frame = pd.DataFrame(rows)
    return app.test_client().post('/api/longitudinal/analyze', data={'file': (io.BytesIO(frame.to_csv(index=False).encode()), 'rx.csv'),
        'mapping': json.dumps(mapping), 'ack': 'yes', 'mode': 'all_dates', 'base_method': 'ED95'})


ROWS = {'HID': ['P1', 'P1'], 'PRESCR_DATE': ['2024-01-02'] * 2, 'DRUG': ['olanzapine 10mg tab', 'risperidone 2mg tab'], '1회정수': ['1', '0.5'], '횟수': ['2', '2']}


def test_daily_is_dose_times_frequency():
    response = analyze(ROWS, {**BASE, 'daily': '', 'per_dose': '1회정수', 'times': '횟수'})
    assert response.status_code == 200
    detail = pd.read_excel(io.BytesIO(response.data), sheet_name='AuditTrail')
    assert list(detail['daily_tablets'].astype(str)) == ['2', '1']
    assert list(detail['daily_mg']) == [20.0, 2.0]
    assert all('1회 정 수 × 1일 횟수' in str(v) or 'daily_from_dose_and_times' in str(v) for v in detail['adjustments'])


def test_per_day_column_wins_when_both_are_chosen():
    rows = {**ROWS, 'TABS_PER_DAY': ['3', '3']}
    response = analyze(rows, {**BASE, 'daily': 'TABS_PER_DAY', 'per_dose': '1회정수', 'times': '횟수'})
    detail = pd.read_excel(io.BytesIO(response.data), sheet_name='AuditTrail')
    assert list(detail['daily_mg']) == [30.0, 6.0]


def test_one_of_the_pair_is_not_enough():
    response = analyze(ROWS, {**BASE, 'daily': '', 'per_dose': '1회정수', 'times': ''})
    assert response.status_code == 400 and '1회 정 수와 1일 횟수' in response.get_json()['error']


def test_mg_in_the_per_dose_column_is_not_counted_as_tablets():
    rows = {**ROWS, '1회정수': ['10mg', '2mg']}
    response = analyze(rows, {**BASE, 'daily': '', 'per_dose': '1회정수', 'times': '횟수'})
    results = pd.read_excel(io.BytesIO(response.data), sheet_name='Results')
    assert results.filter(like='ED95').iloc[0, 0] in ('—', None) or pd.isna(results.filter(like='ED95').iloc[0, 0])


def test_a_column_named_1회량_is_never_chosen_automatically():
    frame = pd.DataFrame({'HID': ['P1'], 'PRESCR_DATE': ['2024-01-02'], 'DRUG': ['olanzapine 10mg tab'], '1회량': ['10'], 'TIMES_PER_DAY': ['2']})
    data = app.test_client().post('/api/longitudinal/inspect', data={'file': (io.BytesIO(frame.to_csv(index=False).encode()), 'rx.csv')}).get_json()
    assert data['mapping']['per_dose'] == '' and data['mapping']['times'] == 'TIMES_PER_DAY'
