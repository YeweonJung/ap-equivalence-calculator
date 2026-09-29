import io
from openpyxl import load_workbook
from app import app
from services.frames import convert_frame, parse_frames
from services.result_notes import with_result_notes


from tests.workbook_helpers import records as workbook_rows


def test_no_supported_factor_is_not_reported_as_success():
    item=convert_frame(parse_frames('blonanserin 8mg QD')[0],['DDD','CMD'])
    assert item['status']=='missing_factor'
    assert item['ok'] is False
    assert '계수' in item['error']
    assert 'DDD' in item['error'] and 'CMD' in item['error']


def test_no_factor_is_in_errors_and_medication_explanation():
    text='id,cpz,raw_redcap_event_name,raw_med_aps,olz\nTEST,9999,baseline,"blonanserin 8mg, quetiapine 50mg",999\n'
    response=app.test_client().post('/upload',data={'file':(io.BytesIO(text.encode()),'review.csv')})
    assert response.status_code==200
    wb=load_workbook(io.BytesIO(response.data),read_only=True)
    errors=workbook_rows(wb,'Review')
    assert any('blonanserin' in r['original'] and '계수' in r['error'] for r in errors)
    medication=workbook_rows(wb,'MedicationResults')[0]
    assert '계수' in medication['환산 근거']
    result=workbook_rows(wb,'Results')[0]
    assert result['DDD (OLZ mg/day)'] is None
    assert '환산계수 없음' in result['확인할 내용']
    assert any('DDD' in r['error'] for r in errors)
    wb.close()


def test_method_failure_reason_is_not_hidden_by_another_input_error():
    result=with_result_notes([{'patient_id':'TEST'}],[
        {'patient':'TEST','status':'converted','original':'paliperidone 75mg PP1M',
         'unavailable_methods':'CMD, WOODS'},
        {'patient':'TEST','status':'unsupported_formulation','original':'aripiprazole 300mg LAI'}
    ],[{'patient':'TEST','original':'aripiprazole 300mg LAI','error':'주사 투여간격 확인'}],
      [{'patient_id':'TEST','method':'CMD','status':'incomplete'}])[0]
    assert 'paliperidone 75mg PP1M' in result['확인할 내용']
    assert 'CMD, WOODS' in result['확인할 내용']
    assert '주사 투여간격 확인' in result['확인할 내용']


def test_partial_method_support_keeps_calculated_values():
    item=convert_frame(parse_frames('risperidone 2mg QD')[0],['DDD','CPZ_FGA'])
    assert item['ok'] and item['status']=='converted'
    assert item['conversions'][0]['value']==4
    assert item['conversions'][1]['value'] is None
