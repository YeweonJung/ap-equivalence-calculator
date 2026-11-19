import io

from app import app

DATED = 'HID,PRESCR_DATE,DRUG,TABS_PER_DAY\n001,2026-10-19,Risperidone 2mg tab,1\n'.encode()


def test_web_upload_of_dated_records_goes_to_the_linking_page():
    response = app.test_client().post('/upload', data={'file': (io.BytesIO(DATED), 'rx.csv'), 'dated': 'page'})
    assert response.status_code == 409
    data = response.get_json()
    assert data['redirect'] == '/longitudinal?from=upload'
    assert '열을 직접 연결' in data['error']


def test_linking_page_explains_why_after_redirect():
    client = app.test_client()
    assert '이 화면으로 옮겼습니다' in client.get('/longitudinal?from=upload').get_data(as_text=True)
    assert '이 화면으로 옮겼습니다' not in client.get('/longitudinal').get_data(as_text=True)


def test_linking_page_says_each_box_lists_the_columns():
    page = app.test_client().get('/longitudinal').get_data(as_text=True)
    assert '칸마다 맞는 열을 고르세요' in page
    script = app.test_client().get('/static/longitudinal.js').get_data(as_text=True)
    assert 'build([], {});' in script and 'lj_wait' in script
