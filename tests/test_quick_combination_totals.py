import math
import pytest
from app import app, METHODS
from services.converter import convert_drug, normalize_target

@pytest.mark.parametrize('drugs', [[('risperidone', 2), ('olanzapine', 5)], [('risperidone', 2), ('olanzapine', 5), ('quetiapine', 100)]])
def test_all_method_combination_totals(drugs):
    data = app.test_client().post('/api/parse', json={'text': ', '.join(f'{drug} {dose}mg' for drug, dose in drugs)}).get_json()
    assert len(data['items']) == len(drugs)
    assert {t['method'] for t in data['totals']} == set(METHODS)
    for total in data['totals']:
        values = []
        for drug, dose in drugs:
            try:
                values.append(convert_drug(drug, dose, total['method'], normalize_target(total['method'])))
            except LookupError:
                pass
        assert total['unresolved_count'] == len(drugs) - len(values)
        if len(values) == len(drugs):
            assert total['total_equivalent_dose_mg'] == pytest.approx(round(math.fsum(values), 4))
        else:
            assert total['total_equivalent_dose_mg'] is None
            assert total['partial_equivalent_dose_mg'] == (round(math.fsum(values), 4) if values else None)


def test_unknown_does_not_become_complete_total():
    data = app.test_client().post('/api/parse', json={'text': 'risperidone 2mg, olanzapine 5mg, unknowndrug 10mg'}).get_json()
    assert all(t['total_equivalent_dose_mg'] is None and t['unresolved_count'] >= 1 for t in data['totals'])
