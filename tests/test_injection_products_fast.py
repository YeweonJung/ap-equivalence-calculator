import io
import re

import pytest
from app import app
from services.frames import drug_mentions, _outside
from services.parser import alias_map


@pytest.mark.parametrize('text,oral,days,dose', [
    ('UZEDY 50mg SC monthly', 2, 30, 50),
    ('UZEDY 75mg monthly', 3, 30, 75),
    ('UZEDY 100mg monthly', 4, 30, 100),
    ('UZEDY 125mg monthly', 5, 30, 125),
    ('UZEDY 100mg q2mo', 2, 60, 100),
    ('UZEDY 150mg q2mo', 3, 60, 150),
    ('UZEDY 200mg q2mo', 4, 60, 200),
    ('UZEDY 250mg q2mo', 5, 60, 250),
    ('PERSERIS 90mg SC monthly', 3, 30, 90),
    ('PERSERIS 120mg monthly', 4, 30, 120),
    ('Risperdal Consta 25mg IM q2w', None, 14, 25),
])
def test_label_product_mappings(text, oral, days, dose):
    data = app.test_client().post('/api/parse', json={'text': text}).get_json()
    assert len(data['items']) == 1
    item = data['items'][0]
    assert item['status'] == 'converted'
    assert item['oral_equivalent_mg'] == oral
    assert item['interval_days'] == days
    assert item['oral_bridge_source'].startswith('https://')
    ddd = next(c for c in item['conversions'] if c['method'] == 'DDD')
    assert ddd['value'] == pytest.approx(round(dose / days / 2.7 * 300, 4))
    if oral is None:
        assert all(c['value'] is None for c in item['conversions'] if c['method'] != 'DDD')


@pytest.mark.parametrize('text', [
    'UZEDY 100mg', 'UZEDY 100mg IM monthly', 'UZEDY 100mg IV monthly',
    'UZEDY 90mg monthly', 'UZEDY 100mg q4w', 'UZEDY 100mg loading monthly',
    'PERSERIS 90mg q2mo', 'PERSERIS 90mg IM monthly',
    'risperidone 90mg SC monthly', 'Consta 25mg SC q2w', 'Consta 25mg',
    'UZEDY PERSERIS 100mg monthly',
])
def test_ambiguous_product_input_is_not_calculated(text):
    data = app.test_client().post('/api/parse', json={'text': text}).get_json()
    assert all(c['value'] is None for item in data['items'] for c in item['conversions'])


def test_combined_matcher_agrees_with_original_algorithm():
    texts = [f'{alias} 2mg, risperdal consta 25mg q2w (olz 10mg)' for alias in alias_map]
    texts += [' / '.join(alias_map), 'RİSPERİDONE 2mg', 'ris 2, olz 5']
    for text in texts:
        hits = []
        for alias, name in alias_map.items():
            for match in re.finditer(r'(?<![\w])' + re.escape(alias) + r'(?![a-z가-힣])', _outside(text), re.I):
                hits.append((match.start(), match.end(), name))
        chosen = []
        for hit in sorted(hits, key=lambda h: (h[0], -(h[1]-h[0]))):
            if not chosen or hit[0] >= chosen[-1][1]:
                chosen.append(hit)
        assert drug_mentions(text) == chosen
