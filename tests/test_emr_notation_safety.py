"""Prescription text from EMR exports: dispensing notes, unlabelled numbers and separate columns.

Each case was found by feeding real-looking export text through the parser (2026-11-20).
A wrong daily dose must never come back as a confident value: it is either right or held.
"""
import io

import pytest
from openpyxl import Workbook, load_workbook

from app import app, METHODS
from services.frames import parse_frames, convert_frame, blank_id_cells


def items(text):
    return [convert_frame(f, METHODS) for f in parse_frames(blank_id_cells(text))]


@pytest.mark.parametrize('text', [
    'risperidone 2mg bid 56T',           # total dispensed read as tablets per dose -> was 224 mg
    'risperidone 2mg bid 28 tabs',       # was 112 mg
    'risperidone 2mg 56T',
    'risperidone 2mg 1T bid 14일분 28T',  # two tablet counts
    'risperidone 2mg 2 bid',             # unlabelled 2: tablets or nothing? was 4 mg with no warning
    'risperidone 2mg bid 28',
    '리스페리돈 2mg 1 2 28',
])
def test_total_quantity_or_unlabelled_number_is_held(text):
    found = items(text)
    assert len(found) == 1 and found[0]['status'] == 'review' and found[0]['daily_dose_mg'] is None


@pytest.mark.parametrize('text,daily', [
    ('risperidone 2mg 1T bid 식후30분', 4), ('risperidone 2mg 1T 1일 2회 식후 30분 28일', 4),
    ('risperidone 2mg 1T bid 원외 28일', 4), ('risperidone 2mg 1T bid 투약일수 28', 4),
    ('risperidone 2mg 1T bid 처방일수 28일', 4), ('risperidone 2mg bid 총 56정', 4),
    ('risperidone 2mg 1T bid for 28 days', 4), ('risperidone 2mg 1T bid 밤 10시', 4),
    ('risperidone 2mg 1T bid (총 56T)', 4), ('risperidone 2mg bid #28', 4), ('risperidone 2mg bid x 28', 4),
    ('risperidone 2mg 아침저녁 1T씩', 4),         # was 2 mg plus a stray fragment
    ('리스페리돈 2mg 1정 2회 28일', 4),             # was 2 mg (once a day assumed)
    ('quetiapine 25mg 2T 3번', 150),
    ('risperidone 2mg 2T 2회 분복', 4),            # 2 tablets divided into two doses
    ('risperidone 2mg bid daily', 4), ('risperidone 2mg 1일 2회 매일', 4),   # were held as conflicting
    ('risperidone 2mg 1 bid', 4), ('quetiapine 25mg 6T 분3', 150), ('risperidone 2mg bid 2024-01-02', 4),
])
def test_dispensing_notes_stay_with_the_medication(text, daily):
    found = items(text)
    assert len(found) == 1, [(i['drug'], i['status']) for i in found]
    assert found[0]['status'] == 'converted' and found[0]['daily_dose_mg'] == daily


def test_numbered_list_markers_are_not_drugs():
    found = items('1. risperidone 2mg bid 2. olanzapine 10mg hs')
    assert [(i['drug'], i['daily_dose_mg']) for i in found] == [('risperidone', 4), ('olanzapine', 10)]


def upload(rows):
    book = Workbook()
    book.active.append(['id', 'med', 'dose', 'unit', 'frequency'])
    for row in rows:
        book.active.append(list(row))
    data = io.BytesIO()
    book.save(data)
    data.seek(0)
    response = app.test_client().post('/upload', data={'file': (data, 't.xlsx'), 'method': 'ALL'},
                                      content_type='multipart/form-data')
    assert response.status_code == 200
    sheet = load_workbook(io.BytesIO(response.data))['MedicationResults']
    return {r[0]: r[6] for r in sheet.iter_rows(min_row=2, values_only=True) if r[0] is not None}


def test_frequency_column_is_used_when_the_drug_cell_has_the_strength():
    daily = upload([
        ('P1', 'risperidone 2mg', None, None, 'bid'),      # was 2 mg: the frequency column was ignored
        ('P2', 'risperidone 2mg', 2, 'mg', 2),
        ('P3', 'risperidone 2mg 1T', None, None, 'bid'),
        ('P4', 'risperidone', 2, 'mg', '2회'),             # was held
        ('P5', 'risperidone', 2, 'mg', '하루 2번'),         # was held
        ('P6', 'risperidone', 2, 'mg', '아침저녁'),          # was held
        ('P7', 'risperidone 2mg', 4, 'mg', 'bid'),        # strength and dose column disagree
        ('P8', 'risperidone 2mg', 2, None, 'bid'),        # 2 = strength or 2 tablets?
        ('P9', 'risperidone 2mg, olanzapine 10mg', None, None, 'bid'),
        ('P10', 'risperidone 2mg bid', None, None, 'tid'),
    ])
    assert [daily[p] for p in ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')] == [4] * 6
    assert [daily[p] for p in ('P7', 'P8', 'P9', 'P10')] == [None] * 4
