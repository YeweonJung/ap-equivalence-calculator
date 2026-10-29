import pytest
from app import app
from scripts.verify_korean_products import product_cases,errors_for


@pytest.mark.parametrize('case',list(product_cases()),ids=lambda c:c['id'])
def test_public_korean_product_and_brand_inputs(case):
    response=app.test_client().post('/api/parse',json={'text':case['text']})
    assert response.status_code==200
    assert errors_for(case,response.json['items'])==[]


@pytest.mark.parametrize('text,active',[
    ('아빌리파이메인테나주사400밀리그램(아리피프라졸일수화물)_(0.416g/2mL) q4w',400),
    ('인베가서스티나주사156mg(팔리페리돈팔미테이트)_(0.156g/1mL) q1mo',100),
    ('인베가트린자주사(팔리페리돈팔미테이트)_(0.4103g/1.315mL) q3mo',263),
])
def test_korean_active_strength_not_pack_or_salt_mass(text,active):
    item=app.test_client().post('/api/parse',json={'text':text}).json['items'][0]
    assert item['active_moiety_mg']==active and not item['needs_review']
    assert item['original']==text
    assert '심평원' in item['calculation_note'] and item['product_name_source']


@pytest.mark.parametrize('suffix',['q1w','q4w IV','q4w loading','q4w 200mg'])
def test_product_match_does_not_discard_unsafe_prescription_suffix(suffix):
    text='아빌리파이메인테나주사400밀리그램 '+suffix
    item=app.test_client().post('/api/parse',json={'text':text}).json['items'][0]
    assert not item['ok'] and not item['conversions'] and item['needs_review']


def test_prn_injection_is_excluded_not_converted():
    item=app.test_client().post('/api/parse',json={'text':'아빌리파이메인테나주사400밀리그램 q4w PRN'}).json['items'][0]
    assert item['status']=='non_target' and item['prn_excluded']
    assert all(c['value']==0 for c in item['conversions'])


def test_export_alias_in_one_product_is_not_a_second_drug():
    text='설피딘정200mg(설피리드)수출명:피리덴정200mg(설피리드)_(0.2g/1정) BID'
    items=app.test_client().post('/api/parse',json={'text':text+', olanzapine 5mg QD'}).json['items']
    assert len(items)==2
    assert items[0]['drug']=='sulpiride' and items[0]['daily_dose_mg']==400
    assert items[1]['drug']=='olanzapine' and items[1]['daily_dose_mg']==5


@pytest.mark.parametrize('dose,unit,frequency,expected',[
    ('','','BID',50), ('25','mg','2',50), ('0.025','g','BID',50),
    ('50','mg','BID',None), ('25','','BID',None), ('','','sometimes',None),
])
def test_korean_product_keeps_separate_schedule_and_rejects_dose_conflict(dose,unit,frequency,expected):
    from app import _compose_structured_medication
    from services.structured import structured_frames
    row=dict(dose=dose,unit=unit,frequency=frequency)
    raw='클자핀정25밀리그램(클로자핀)_(25mg/1정)'
    frame,=structured_frames(row,raw,'dose','unit','frequency',_compose_structured_medication)
    assert frame['daily_dose_mg']==expected
    assert frame['needs_review']==(expected is None)


def test_korean_injection_keeps_separate_interval():
    from app import _compose_structured_medication
    from services.structured import structured_frames
    row=dict(frequency='q4w')
    frame,=structured_frames(row,'아빌리파이메인테나주사400밀리그램',None,None,'frequency',_compose_structured_medication)
    assert frame['active_moiety_mg']==400 and frame['interval_days']==28
    assert not frame['needs_review']


def test_normal_product_provenance_is_in_details_without_crowding_summary():
    data=app.test_client().post('/api/parse',json={'text':'클자핀정25밀리그램 QD'}).json
    case,=data['cases']
    assert case['note']==''
    assert '심평원' in case['details'][0]['note']
