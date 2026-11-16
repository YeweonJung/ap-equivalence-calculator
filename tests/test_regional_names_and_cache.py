import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import app
from services.parser import COMPACT_ALIAS_MAP

ROOT = Path(__file__).resolve().parents[1]


def case(text):
    return app.test_client().post('/api/parse', json={'text': text, 'base_method': 'ED95'}).json['cases'][0]


def test_compact_keys_never_reduce_to_digits():
    # '降脂1号树脂' once became the key '1' and turned any Arabic/Chinese line with a 1 into colestyramine.
    assert all(any(c.isalpha() for c in key) for key in COMPACT_ALIAS_MAP)
    assert case('قرص 1')['details'][0]['drug'] != 'colestyramine'


@pytest.mark.parametrize('text, drug, total', [
    ('زيبريكسا 10 ملغ مرتين يوميا', 'olanzapine', 20.0),
    ('再普乐 10mg qd', 'olanzapine', 10.0),
    ('康尔汀 8mg tid', 'perospirone', 7.5),
    ('perospirone 16mg tid', 'perospirone', 15.0),
    ('timiperone 3mg bid', 'timiperone', 11.5385),
    ('cariprazine 3mg qd', 'cariprazine', 10.0),
])
def test_regional_names_and_inada_factors(text, drug, total):
    result = case(text)
    assert result['details'][0]['drug'] == drug
    assert result['total'] == pytest.approx(total, abs=1e-3)


@pytest.mark.parametrize('text', ['美比瑞 100mg q4w', '阿丽唯 400mg q4w', 'Raibyax 6/25mg 1 cap'])
def test_non_reference_lai_and_combinations_are_held(text):
    assert case(text)['total'] is None


def test_regional_entries_keep_their_source_page():
    entries = json.loads((ROOT / 'lookup/regional_brand_names.json').read_text(encoding='utf-8'))['entries']
    assert entries and all(e['source_url'].startswith('http') for e in entries)


def test_cached_name_tables_equal_a_fresh_build():
    code = ('import json,sys; sys.path.insert(0,"."); from services import name_supplement as n; '
            'print(json.dumps([len(n.AP_ALIASES), len(n.OTHER_ALIASES), sorted(n.WORLD_ADDED)[:50], '
            'sorted(n.AP_COMBINATIONS)[:50], sorted(n.ANTIPSYCHOTICS)]))')
    runs = []
    for mode in ('off', None):
        env = {**os.environ, 'NAME_LLM_ENABLED': '0'}
        env.pop('APP_TABLE_CACHE', None)
        if mode:
            env['APP_TABLE_CACHE'] = mode
        runs.append(subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True,
                                   text=True, check=True).stdout.strip().splitlines()[-1])
    assert runs[0] == runs[1]


@pytest.mark.parametrize('text, total', [
    ('善思达 150mg 每4周', 13.636), ('善妥达 350mg 3个月1次', 10.227), ('ゼプリオン 150mg 月1回', 13.636),
    ('ゼプリオンTRI 350mg 3ヶ月に1回', 10.227), ('انفيجا سستينا 150 ملغ كل 4 أسابيع', 13.636),
    ('Risperdal Consta 25mg كل اسبوعين', 6.6138), ('Xeplion 100 mg toutes les 4 semaines', 10.227),
    ('Trevicta 350 mg tous les 3 mois', 10.227),
])
def test_multilingual_injection_intervals(text, total):
    result = case(text)
    assert len(result['details']) == 1
    assert result['total'] == pytest.approx(total, abs=1e-3)
