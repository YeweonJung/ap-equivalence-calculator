from app import app


def parse(text):
    return app.test_client().post('/api/parse', json={'text': text}).json['items']


def test_unmarked_drug_is_oral_even_at_a_large_dose():
    item = parse('aripiprazole 400mg')[0]
    assert item['route'] == 'oral' and item['formulation'] == 'ORAL'
    assert item['daily_dose_mg'] == 400


def test_lai_without_interval_is_injection_with_no_oral_daily_dose():
    item = parse('aripiprazole 400mg(LAI)')[0]
    assert item['route'] == 'injection'
    assert item['status'] == 'unsupported_formulation'
    assert item['daily_dose_mg'] is None and item['conversions'] == []


def test_shared_lai_validates_each_interval_instead_of_rejecting_both():
    text = 'aripiprazole 400mg q4w, paliperidone 150mg PP1M (LAI둘다)'
    items = parse(text)
    assert len(items) == 2
    assert all(i['route'] == 'injection' and i['status'] == 'converted' for i in items)
    assert [i['interval_days'] for i in items] == [28, 30]
    for item in items:
        assert text[item['source_start']:item['source_end']] == item['original']


def test_shared_lai_does_not_invent_missing_interval_or_profile():
    items = parse('aripiprazole 400mg, paliperidone 150mg (LAI둘다)')
    assert len(items) == 2
    assert all(i['route'] == 'injection' for i in items)
    assert all(i['daily_dose_mg'] is None and i['conversions'] == [] for i in items)


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
    assert items[0]['status'] == 'unsupported_formulation'
    assert items[0]['daily_dose_mg'] is None
    assert items[1]['status'] == 'converted' and items[1]['interval_days'] == 30


def test_existing_equivalent_columns_are_not_reconverted():
    import io
    from openpyxl import load_workbook
    csv = 'id,cpz,raw_redcap_event_name,raw_med_aps,olz\nTEST,8200,baseline,risperidone 2mg,999\n'
    response = app.test_client().post('/upload', data={
        'file': (io.BytesIO(csv.encode()), 'prior_equivalents.csv')})
    assert response.status_code == 200
    wb = load_workbook(io.BytesIO(response.data))
    values = list(wb['Results'].values)
    result = dict(zip(values[0], values[1]))
    assert result['DDD (CPZ mg/day)'] == 120
    audit = list(wb['AuditTrail'].values)
    assert len(audit) == 2
    row = dict(zip(audit[0], audit[1]))
    assert row['medication_column'] == 'raw_med_aps'
    assert row['route'] == 'oral'
