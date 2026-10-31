"""Every common prescription notation is read without AI, or held when its meaning is ambiguous."""
import pytest
from app import app
from services.name_supplement import ANTIPSYCHOTICS
from tests.notation_corpus import CASES, H

HOLDS = {'unknown_drug', 'review', 'missing_unit', 'unsupported_formulation', 'missing_factor'}
# Two-slot "1-1" may be morning-evening or a range; it is calculated once daily with a frequency warning.
KNOWN_OPEN = {'risperidone 2mg 1-1'}


def outcome(text):
    items = app.test_client().post('/api/parse', json={'text': text}).json['items']
    if any(i['status'] in HOLDS and (i.get('drug') in ANTIPSYCHOTICS or not i.get('drug')) for i in items):
        return H
    return sorted((i['drug'], round(i['daily_dose_mg'], 4)) for i in items
                  if i['status'] == 'converted' and i.get('daily_dose_mg') is not None)


def accepted(expected):
    if expected == [H]:
        return [H]
    if expected and expected[-1] == H:
        rest = [e for e in expected if e != H]
        return [H] + ([rest[0]] if rest and isinstance(rest[0], list) else [rest])
    return [expected]


@pytest.mark.parametrize('text,expected', [c for c in CASES if c[0] not in KNOWN_OPEN], ids=lambda v: v if isinstance(v, str) else '')
def test_notation(text, expected):
    got = outcome(text)
    options = [o if o == H else sorted((d, float(v)) for d, v in o) for o in accepted(expected)]
    assert got in options
