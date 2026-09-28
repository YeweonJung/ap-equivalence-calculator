import pytest
from app import app
from services.lai_support import PRODUCTS, profile_for
from services.parser import alias_map


@pytest.mark.parametrize('name,identity', list(PRODUCTS.items()))
def test_every_registered_product_keeps_ingredient_and_profile(name, identity):
    assert alias_map[name] == identity[0]
    assert profile_for(name.upper() + ' 25mg', identity[0], 25) == identity[1]


@pytest.mark.parametrize('alias,canonical', [
    ('인베가서스티나주100mg PP1M', 'sustenna 100mg PP1M'),
    ('인베가-트린자주사 350mg', 'trinza 350mg'),
    ('INVEGA-TRINZA 350mg', 'trinza 350mg'),
    ('아빌리파이메인테나주400mg q4w', 'maintena 400mg q4w'),
    ('메인테나 주사 400mg q4w', 'maintena 400mg q4w'),
    ('리스페달콘스타주25mg q2w', 'consta 25mg q2w'),
    ('RISPERDAL-CONSTA 25mg q2w', 'consta 25mg q2w'),
    ('ABILIFYASIMTUFII 960mg q2mo', 'asimtufii 960mg q2mo'),
])
def test_alias_api_matches_canonical_product(alias, canonical):
    client = app.test_client()
    a = client.post('/api/parse', json={'text': alias}).get_json()['items']
    b = client.post('/api/parse', json={'text': canonical}).get_json()['items']
    assert len(a) == len(b) == 1
    assert a[0]['status'] == b[0]['status'] == 'converted'
    for key in ('drug', 'lai_profile', 'interval_days', 'active_moiety_mg', 'conversions'):
        assert a[0][key] == b[0][key]


@pytest.mark.parametrize('text', [
    '메인테나주400mg', '리스페달콘스타주25mg',
    '인베가서스티나 인베가트린자 100mg',
    '올란자핀 콘스타주25mg q2w', '메인테나주400mg SC q4w',
])
def test_aliases_do_not_bypass_review(text):
    items = app.test_client().post('/api/parse', json={'text': text}).get_json()['items']
    assert all(c['value'] is None for item in items for c in item['conversions'])
