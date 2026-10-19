import io
import pytest
from app import app
from scripts.verify_mixed_prescriptions import ORDER, regimens, check_case, check_workbook, upload_data


@pytest.mark.parametrize('base',ORDER)
@pytest.mark.parametrize('prescription',regimens(),ids=lambda p:p['id'])
def test_mixed_prescription_retains_base_and_first_available_fallback(prescription,base):
    response=app.test_client().post('/api/parse',json={
        'text':', '.join(r['text'] for r in prescription['rows']),'base_method':base})
    assert response.status_code==200
    case,=response.json['cases']
    check_case(case,prescription,base)


@pytest.mark.parametrize('base',ORDER)
def test_mixed_prescriptions_keep_same_values_in_all_export_paths(base):
    client, prescriptions=app.test_client(),regimens()
    p=prescriptions[1]
    response=client.post('/api/export',json={'text':', '.join(r['text'] for r in p['rows']),'base_method':base})
    assert response.status_code==200
    check_workbook(response.data,[p],base,quick=True)
    for dated in (False,True):
        response=client.post('/upload',data={'base_method':base,'file':(io.BytesIO(upload_data(prescriptions,dated)),'mixed.csv')})
        assert response.status_code==200
        check_workbook(response.data,prescriptions,base)
