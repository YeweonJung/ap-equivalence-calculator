import pytest
from app import app


def parse(text):
    return app.test_client().post('/api/parse', json={'text': text}).json['items']


def test_unmarked_drug_is_oral_even_at_a_large_dose():
    item = parse('aripiprazole 400mg')[0]
    assert item['route'] == 'oral' and item['formulation'] == 'ORAL'
    assert item['daily_dose_mg'] == 400


def test_lai_without_product_or_interval_assumes_once_monthly_never_oral():
    item = parse('aripiprazole 400mg(LAI)')[0]
    assert item['route'] == 'injection' and item['status'] == 'converted'
    assert item['lai_profile'] == 'ARI_1M' and item['interval_days'] == 28
    assert item['daily_dose_mg'] == pytest.approx(400 / 28) and item['interval_assumed']
    assert '가정' in item['calculation_note']
    assert item['oral_equivalent_mg'] is None  # no oral bridge: oral factors are never reused


def test_unlisted_strength_without_interval_stays_blank():
    for text in ('aripiprazole 200mg(LAI)', 'paliperidone 200mg(LAI)', 'aripiprazole 400mg LAI q2w'):
        item = parse(text)[0]
        assert item['status'] == 'unsupported_formulation' and item['daily_dose_mg'] is None


def test_shared_lai_validates_each_interval_instead_of_rejecting_both():
    text = 'aripiprazole 400mg q4w, paliperidone 150mg PP1M (LAI둘다)'
    items = parse(text)
    assert len(items) == 2
    assert all(i['route'] == 'injection' and i['status'] == 'converted' for i in items)
    assert [i['interval_days'] for i in items] == [28, 30]
    for item in items:
        assert text[item['source_start']:item['source_end']] == item['original']


def test_shared_lai_without_intervals_uses_each_drugs_once_monthly_assumption():
    items = parse('aripiprazole 400mg, paliperidone 150mg (LAI둘다)')
    assert len(items) == 2
    assert all(i['route'] == 'injection' and i['interval_assumed'] for i in items)
    assert [(i['lai_profile'], i['interval_days']) for i in items] == [('ARI_1M', 28), ('PP1M', 30)]


def test_local_lai_does_not_spread_to_neighboring_oral_medication():
    items = parse('paliperidone 150mg PP1M, quetiapine 100mg')
    assert [i['route'] for i in items] == ['injection', 'oral']
    assert items[1]['daily_dose_mg'] == 100


def test_explicit_korean_route_annotations():
    oral = parse('paliperidone 9mg(MED;경구)')[0]
    injection = parse('paliperidone 100mg(1개월 지속형 주사, PP1M)')[0]
    assert oral['route'] == 'oral' and oral['formulation'] == 'ORAL'
    assert injection['route'] == 'injection' and injection['interval_days'] == 30


def test_shared_lai_does_not_borrow_another_drugs_interval():
    items = parse('aripiprazole 400mg, paliperidone 150mg PP1M (LAI둘다)')
    # aripiprazole uses its own 28-day assumption, never paliperidone's PP1M 30 days.
    assert items[0]['interval_days'] == 28 and items[0]['lai_profile'] == 'ARI_1M'
    assert items[1]['status'] == 'converted' and items[1]['interval_days'] == 30


def test_existing_equivalent_columns_are_not_reconverted():
    import io
    from openpyxl import load_workbook
    csv = 'id,cpz,raw_redcap_event_name,raw_med_aps,olz\nTEST,8200,baseline,risperidone 2mg,999\n'
    response = app.test_client().post('/upload', data={
        'file': (io.BytesIO(csv.encode()), 'prior_equivalents.csv')})
    assert response.status_code == 200
    wb = load_workbook(io.BytesIO(response.data))
    from tests.workbook_helpers import records
    result = records(wb, 'Results')[0]
    assert result['DDD (OLZ mg/day)'] == 4
    audit = list(wb['MedicationResults'].values)
    assert len(audit) == 2
    row = dict(zip(audit[0], audit[1]))
    assert row['medication_column'] == 'raw_med_aps'
    assert row['daily_dose_mg'] == 2
