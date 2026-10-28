import io
import pytest
from openpyxl import load_workbook
from app import app
from services.converter import convert_drug, normalize_target
from services.result_summary import METHOD_ORDER, TARGETS
from tests.workbook_helpers import records


@pytest.mark.parametrize('base', METHOD_ORDER)
def test_selected_base_matches_quick_upload_and_dated_with_all_method_columns(base):
    client=app.test_client()
    text='olanzapine 5mg QD, paliperidone 6mg QD'
    data=client.post('/api/parse',json={'text':text,'base_method':base}).json
    case,=data['cases']
    assert case['base']==base
    for row in case['details']:
        try:
            expected=convert_drug(row['drug'],row['dose'],base,normalize_target(base))
        except LookupError:
            continue
        assert row['actual']==base
        assert row['value']==pytest.approx(expected)
    inputs=[
        client.post('/api/export',json={'text':text,'base_method':base}),
        client.post('/upload',data={'base_method':base,'file':(io.BytesIO(b'patient_id,medication\n001,olanzapine 5mg QD\n001,paliperidone 6mg QD\n'),'flat.csv')}),
        client.post('/upload',data={'base_method':base,'file':(io.BytesIO(b'HID,PRESCR_DATE,DRUG,TABS_PER_DAY\n001,2026-10-19,Olanzapine 5mg tab,1\n001,2026-10-19,Paliperidone 6mg tab,1\n'),'dated.csv')}),
    ]
    for response in inputs:
        assert response.status_code==200
        wb=load_workbook(io.BytesIO(response.data))
        summary,=records(wb,'보완합계')
        assert summary['기본 방법']==base and summary['보완 총합 (mg/day)']==case['total']
        rows=records(wb,'보완근거')
        assert len(rows)==2
        for row,detail in zip(rows,case['details']):
            assert row['적용 방법']==detail['actual']
            for method in METHOD_ORDER:
                value=row[f'{method} ({TARGETS[method]} mg/day)']
                assert value == pytest.approx(detail[method]) if detail[method] is not None else value is None


@pytest.mark.parametrize('base',['ALL','wrong',42,[],{}])
def test_invalid_base_rejected_before_any_calculation(base):
    for endpoint in ['/api/parse','/api/export']:
        response=app.test_client().post(endpoint,json={'text':'olanzapine 5mg QD','base_method':base})
        assert response.status_code==400


def test_complete_base_has_no_supplement_and_partial_never_becomes_total():
    client=app.test_client()
    complete=client.post('/api/parse',json={'text':'olanzapine 5mg QD, risperidone 2mg QD','base_method':'CMD'}).json['cases'][0]
    assert complete['case_id']=='CMD' and complete['supplemented']==0 and complete['complement']==''
    partial=client.post('/api/parse',json={'text':'paliperidone 6mg QD, unknownxyz 2mg','base_method':'CMD'}).json['cases'][0]
    assert partial['total'] is None and partial['partial']==10 and partial['missing']==1
