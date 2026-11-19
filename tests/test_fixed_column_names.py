"""Uploads read only fixed column names and stop with a message instead of guessing (2026-11-19)."""
import io
import unicodedata

import pandas as pd
import pytest

from app import app
from services.column_detector import column_problem, detect_columns, detect_medication_groups


def upload(content, name='x.csv'):
    data = content.encode('utf-8-sig') if isinstance(content, str) else content
    return app.test_client().post('/upload', data={'file': (io.BytesIO(data), name), 'method': 'ALL'})


def frame(*columns):
    return pd.DataFrame([['1'] * len(columns)], columns=list(columns))


@pytest.mark.parametrize('header', ['약물', 'medication', 'Drug', ' 약 물 ', '약물​', 'ｍｅｄｉｃａｔｉｏｎ',
                                    unicodedata.normalize('NFD', '약물')])
def test_drug_header_spellings_that_mean_the_same_name(header):
    assert detect_columns(frame('환자ID', header))['medication_column'] == header


@pytest.mark.parametrize('header', ['약물명', '처방', 'aps', 'medications', '약물(처방)', 'raw_med_aps'])
def test_other_drug_headers_are_not_read(header):
    assert detect_columns(frame('환자ID', header))['medication_column'] is None


@pytest.mark.parametrize('header', ['환자ID', '환자 ID', 'id', 'Patient_ID', unicodedata.normalize('NFD', '환자ID')])
def test_id_header_spellings(header):
    assert detect_columns(frame(header, '약물'))['patient_column'] == header


@pytest.mark.parametrize('columns, words', [
    (('환자ID', '약물', 'medication'), '같은 역할'),
    (('ID', '환자ID', '약물'), '같은 역할'),
    (('환자ID', '약물', '약물1', '용량1'), '번호'),
    (('환자ID', '약물1', '용량1', '용량2'), '짝'),
])
def test_ambiguous_layouts_are_refused(columns, words):
    assert words in column_problem(frame(*columns))
    response = upload(','.join(columns) + '\n' + ','.join(['P1', 'olanzapine 5mg'] + ['1'] * (len(columns) - 2)) + '\n')
    assert response.status_code == 400 and words in response.get_data(as_text=True)


def test_numbered_groups_pair_by_number():
    groups = detect_medication_groups(frame('환자ID', '약물1', '용량1', '약물 2', '용량_2'))
    assert [(g['medication_column'], g['dose_column']) for g in groups] == [('약물1', '용량1'), ('약물 2', '용량_2')]
    assert column_problem(frame('환자ID', '약물1', '용량1', '약물 2', '용량_2')) is None


def test_missing_columns_stop_with_a_message():
    response = upload('환자번호,처방내역\nP1,olanzapine 5mg\n')
    assert response.status_code == 400 and '약물이 적힌 열' in response.get_data(as_text=True)
    response = upload('No,약물\n1,olanzapine 5mg\n')
    assert response.status_code == 400 and '환자 번호가 적힌 열' in response.get_data(as_text=True)


def test_skipped_sheets_and_ids_shared_by_sheets_are_reported():
    book = io.BytesIO()
    with pd.ExcelWriter(book, engine='openpyxl') as writer:
        pd.DataFrame({'환자ID': ['P1'], '약물': ['olanzapine 5mg']}).to_excel(writer, sheet_name='a', index=False)
        pd.DataFrame({'환자ID': ['P1'], '약물': ['risperidone 2mg']}).to_excel(writer, sheet_name='b', index=False)
        pd.DataFrame({'메모': ['처방 아님']}).to_excel(writer, sheet_name='memo', index=False)
    response = upload(book.getvalue(), 'x.xlsx')
    assert response.status_code == 200
    assert response.headers['X-Upload-Notes'] == 'skipped=1;shared=1'


def test_sample_file_reads_cleanly():
    sample = app.test_client().get('/sample').data
    response = upload(sample, 'sample.xlsx')
    assert response.status_code == 200
    assert response.headers['X-Upload-Notes'] == 'skipped=0;shared=0'


def test_header_below_a_title_row_is_found():
    response = upload('처방 목록 2026\n환자ID,약물\nP1,olanzapine 5mg\n')
    assert response.status_code == 200 and response.headers['X-Medication-Lines'] == '1'


def test_date_upload_with_the_korean_names_is_mapped():
    response = upload('환자ID,처방일,약물,하루정수,처방일수\nP1,2026-01-02,olanzapine 5mg,2,28\n')
    assert response.status_code == 200, response.get_data(as_text=True)[-400:]


def test_date_upload_missing_columns_names_them_in_korean():
    response = upload('환자ID,처방일,약물\nP1,2026-01-02,olanzapine 5mg\n')
    assert response.status_code == 400 and '하루정수' in response.get_data(as_text=True)


def test_spaces_around_an_id_do_not_split_a_patient():
    response = upload('환자ID,약물\nP1,olanzapine 5mg\n P1 ,risperidone 2mg\n')
    rows = pd.read_excel(io.BytesIO(response.data), sheet_name='Results')
    assert len(rows) == 1
