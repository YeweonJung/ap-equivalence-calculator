import pandas as pd

from services.column_detector import detect_columns


def test_unusual_header_with_drug_names_is_found():
    df = pd.DataFrame({'id': ['1', '2'], 'aps': ['ris 3, olan 10', 'qtp 10, zip 10']})
    assert detect_columns(df)['medication_column'] == 'aps'


def test_column_without_drug_names_is_not_taken():
    df = pd.DataFrame({'id': ['1', '2'], 'memo': ['외래 방문', '입원']})
    assert detect_columns(df)['medication_column'] is None
