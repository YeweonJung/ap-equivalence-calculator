import io
import pytest
from openpyxl import load_workbook
from app import app
from services.converter import convert_drug
from services.frames import convert_frame, parse_frames
from tests.workbook_helpers import records


@pytest.mark.parametrize('method,drug,unit', [
    ('CMD', 'olanzapine', 'OLZ'), ('DDD', 'olanzapine', 'OLZ'),
    ('GARDNER', 'olanzapine', 'OLZ'), ('MED', 'olanzapine', 'OLZ'),
    ('CMD_DIRECT', 'olanzapine', 'OLZ'), ('CMD_INDIRECT', 'olanzapine', 'OLZ'),
    ('ED95', 'risperidone', 'RIS'), ('WOODS', 'chlorpromazine', 'CPZ'),
    ('CPZ_FGA', 'chlorpromazine', 'CPZ'),
])
def test_reference_identity_in_api_and_export(method, drug, unit):
    assert convert_drug(drug, 10, method) == pytest.approx(10)
    data = app.test_client().post('/api/parse', json={'text': drug + ' 10mg QD'}).get_json()
    result = next(c for c in data['items'][0]['conversions'] if c['method'] == method)
    assert result['target'] == drug and result['value'] == pytest.approx(10)
    for source in [f'patient_id,medication\n001,{drug} 10mg QD\n',
                   f'HID,PRESCR_DATE,DRUG,TABS_PER_DAY\n001,2026-09-01,{drug} 10mg tab,1\n']:
        response = app.test_client().post('/upload', data={'method': method, 'file': (io.BytesIO(source.encode()), 'synthetic.csv')})
        wb = load_workbook(io.BytesIO(response.data))
        assert records(wb, 'Results')[0][f'{method} ({unit} mg/day)'] == pytest.approx(10)


def test_published_gardner_anchor_and_depot_ddd_reference():
    assert convert_drug('chlorpromazine', 600, 'GARDNER') == pytest.approx(20)
    item = convert_frame(parse_frames('Risperdal Consta 25mg IM q2w')[0], ['DDD'])
    result = item['conversions'][0]
    assert item['oral_equivalent_mg'] is None
    assert result['target'] == 'olanzapine'
    assert result['value'] == pytest.approx(25 / 14 / 2.7 * 10, abs=0.0001)
    assert result['basis'] == 'WHO depot DDD'
