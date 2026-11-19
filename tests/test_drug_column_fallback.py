import pandas as pd

from services.column_detector import detect_columns


def test_unusual_header_with_drug_names_is_found():
    df = pd.DataFrame({'id': ['1', '2'], 'aps': ['ris 3, olan 10', 'qtp 10, zip 10']})
    assert detect_columns(df)['medication_column'] == 'aps'


def test_column_without_drug_names_is_not_taken():
    df = pd.DataFrame({'id': ['1', '2'], 'memo': ['외래 방문', '입원']})
    assert detect_columns(df)['medication_column'] is None


import pytest


@pytest.mark.parametrize('columns, expected', [
    (['Pt ID', 'APs'], ('Pt ID', 'APs', None, None)),
    (['환자 ID', '항정신병약물'], ('환자 ID', '항정신병약물', None, None)),
    (['No', '환자번호', '약'], ('환자번호', '약', None, None)),
    (['subject', 'meds', 'mg/day', 'freq'], ('subject', 'meds', 'mg/day', 'freq')),
    (['患者ID', '薬剤名', '用量'], ('患者ID', '薬剤名', '用量', None)),
    (['patient', 'drug', '투약량', '투약횟수'], ('patient', 'drug', '투약량', '투약횟수')),
    (['id', '약물명', '약물용량'], ('id', '약물명', '약물용량', None)),
    (['identifiant', 'médicament', 'posologie', 'fréquence'], ('identifiant', 'médicament', 'posologie', 'fréquence')),
])
def test_common_header_variants(columns, expected):
    row = ['1', 'olanzapine', '10', '1'][:len(columns)]
    found = detect_columns(pd.DataFrame([row], columns=columns))
    assert (found['patient_column'], found['medication_column'], found['dose_column'], found['frequency_column']) == expected


def test_short_words_need_the_whole_header():
    found = detect_columns(pd.DataFrame([['1', 'olanzapine 10mg', '3']], columns=['id', 'Medication', 'median']))
    assert found['medication_column'] == 'Medication'
