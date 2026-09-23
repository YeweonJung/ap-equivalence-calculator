from services.result_notes import with_result_notes


def test_missing_factor_is_distinct_from_unrecognized_input():
    row = {'patient_id': 'P1', 'CMD': 389, 'CPZ_FGA': None}
    result = with_result_notes([row], [{'patient': 'P1', 'status': 'converted'}], [], [
        {'patient_id': 'P1', 'method': 'CMD', 'status': 'complete'},
        {'patient_id': 'P1', 'method': 'CPZ_FGA', 'status': 'incomplete'}])[0]
    assert result['결과 상태'] == '일부 방법 환산 불가'
    assert 'CPZ_FGA' in result['확인할 내용']
    assert result['CMD'] == 389 and result['CPZ_FGA'] is None


def test_missing_prescription_is_not_non_target():
    empty = with_result_notes([{'patient_id': 'P1'}], [], [], [])[0]
    excluded = with_result_notes([{'patient_id': 'P1'}], [
        {'patient': 'P1', 'status': 'non_target'}], [], [])[0]
    assert empty['결과 상태'] == '약물 입력 없음'
    assert excluded['결과 상태'] == '환산 대상 없음'


def test_input_warning_keeps_existing_total_but_requires_review():
    result = with_result_notes([{'patient_id': 'P1', 'CMD': 100}], [
        {'patient': 'P1', 'status': 'converted', 'original': 'drug 1mg',
         'needs_review': True, 'warning': '복용 빈도 없음'}], [], [
        {'patient_id': 'P1', 'method': 'CMD', 'status': 'complete'}])[0]
    assert result['CMD'] == 100
    assert result['결과 상태'] == '입력 확인 필요'
    assert '복용 빈도 없음' in result['확인할 내용']
