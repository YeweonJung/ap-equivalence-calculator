import io
import pytest
from openpyxl import load_workbook
from app import app
from services.result_summary import TARGETS


def upload(drugs, doses, units='mg', frequency='QD'):
    import csv
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['patient_id', 'drug', 'dose', 'unit', 'frequency'])
    writer.writerow(['TEST1', drugs, doses, units, frequency])
    response = app.test_client().post('/upload', data={
        'file': (io.BytesIO(stream.getvalue().encode()), 'parallel.csv')})
    assert response.status_code == 200
    return load_workbook(io.BytesIO(response.data))


def records(wb, name):
    values = list(wb[name].values)
    return [dict(zip(values[0], r)) for r in values[1:]]


@pytest.mark.parametrize('drugs,doses', [
    ('Abilify olanzapine', '10, 15'),
    ('Abilify, olanzapine', '10 15'),
    ('Abilify olanzapine', '10mg 15mg'),
    ('Abilify; olanzapine', '10; 15'),
])
def test_multiple_medications_sum_to_one_patient(drugs, doses):
    wb = upload(drugs, doses)
    result = records(wb, 'Results')
    assert len(result) == 1
    expected = app.test_client().post('/api/parse', json={
        'text': 'Abilify 10mg QD; olanzapine 15mg QD'}).json['totals']
    for total in expected:
        assert result[0][f"{total['method']} ({TARGETS[total['method']]} mg/day)"] == total['total_equivalent_dose_mg']
    assert [a['dose_mg'] for a in records(wb, 'AuditTrail')] == [10, 15]


def test_unknown_names_keep_their_own_doses_without_a_false_total():
    wb = upload('Abilify unknownxyz', '10, 15')
    audit = records(wb, 'AuditTrail')
    assert len(audit) == 2
    assert audit[0]['parsed'] == 'aripiprazole' and audit[0]['dose_mg'] == 10
    assert audit[1]['parsed'] is None and audit[1]['dose_mg'] == 15
    assert records(wb, 'Results')[0]['DDD (CPZ mg/day)'] is None
    check = next(c for c in records(wb, 'PatientChecks') if c['method'] == 'DDD')
    assert check['converted_count'] == 1 and check['unresolved_count'] == 1


def test_space_separated_unknown_names_and_doses_are_not_lost():
    audit = records(upload('unknownxyz, unknownabc', '15 10', frequency=''), 'AuditTrail')
    assert len(audit) == 2
    assert [a['dose_mg'] for a in audit] == [15, 10]
    assert all(a['status'] == 'unknown_drug' for a in audit)


def test_registered_multiword_product_stays_one_medication():
    from services.structured import _parallel_names
    assert _parallel_names(['invega sustenna risperidone'], 2) == ['invega sustenna', 'risperidone']
    assert _parallel_names(['invega sustenna'], 2) == ['invega sustenna']


def test_parallel_frequency_values_pair_in_order():
    audit = records(upload('Risperdal olanzapine', '2 5', frequency='BID QD'), 'AuditTrail')
    assert [a['daily_dose_mg'] for a in audit] == [4, 5]


def test_conflicting_units_never_produce_totals():
    wb = upload('Risperdal olanzapine', '2mg 5mg', units='g')
    assert all(a['status'] == 'review' for a in records(wb, 'AuditTrail'))
    assert records(wb, 'Results')[0]['DDD (CPZ mg/day)'] is None


def test_one_dose_is_not_reused_for_multiple_names():
    wb = upload('Risperdal,olanzapine', '2')
    assert records(wb, 'Results')[0]['DDD (CPZ mg/day)'] is None


@pytest.mark.parametrize('drugs,doses,frequency,expected', [
    ('Abilify clop', '10, 15', 'QD', ['aripiprazole', 'clopenthixol']),
    ('Abilify, rispl', '10, 16', 'QD', ['aripiprazole', 'risperidone']),
    ('Abilify,olx', '10, 17', '', ['aripiprazole', 'olanzapine']),
    ('Abil, zir', '15 10', '', ['aripiprazole', 'ziprasidone']),
])
def test_user_confirmed_sample_aliases_and_missing_frequency(drugs, doses, frequency, expected):
    wb = upload(drugs, doses, frequency=frequency)
    audit = records(wb, 'AuditTrail')
    assert [a['parsed'] for a in audit] == expected
    assert all(a['daily_dose_mg'] == a['dose_mg'] for a in audit)
    result = records(wb, 'Results')[0]
    assert result['GARDNER (CPZ mg/day)'] is not None
    if 'zir' in drugs:
        assert audit[1]['needs_review'] is True
        assert 'REVIEW_REQUIRED' in audit[1]['warning']
        assert audit[1]['original'].startswith('zir ')
        assert audit[1]['match_type'] == 'user_confirmed_alias'
    if not frequency:
        assert all(a['frequency'] == 'ASSUMED_QD' for a in audit)
