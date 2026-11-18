"""Page-level checks added in the 2026-11-18 site review."""
import io
import re

from app import app


def test_empty_upload_is_flagged_with_zero_medication_lines():
    response = app.test_client().post('/upload', data={'file': (io.BytesIO(b'a,b\n1,2'), 'x.csv'), 'method': 'ALL'})
    assert response.status_code == 200
    assert response.headers['X-Medication-Lines'] == '0'


def test_upload_reports_medication_line_count():
    raw = 'ID,처방\nP001,"risperidone 2mg BID, olanzapine 5mg"\n'.encode('utf-8-sig')
    response = app.test_client().post('/upload', data={'file': (io.BytesIO(raw), 'x.csv'), 'method': 'ALL'})
    assert int(response.headers['X-Medication-Lines']) == 2


def test_base_selectors_list_ed95_first():
    client = app.test_client()
    for path, select_id in [('/', 'base-method'), ('/', 'base-method-quick'), ('/longitudinal', 'lg-base')]:
        html = client.get(path).get_data(as_text=True)
        block = re.search(r'<select id="%s"[^>]*>(.*?)</select>' % select_id, html, re.S).group(1)
        assert re.findall(r'<option value="([A-Z0-9_]+)"', block)[0] == 'ED95', (path, select_id)


def test_secondary_pages_share_header_and_tabs():
    client = app.test_client()
    for path, active in [('/longitudinal', '날짜별 분석'), ('/methods', '사용 안내')]:
        html = client.get(path).get_data(as_text=True)
        assert 'class="site-tabs"' in html and '/static/site.css' in html and 'data-lang-select' in html
        assert re.search(r'aria-current="page">%s<' % active, html), path
