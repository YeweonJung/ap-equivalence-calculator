import io
from openpyxl import load_workbook
from app import app


def test_overview_keeps_values_and_explains_blanks():
    raw='patient_id,medication\n001,risperidone 2mg QD\n002,blonanserin 8mg\n'
    response=app.test_client().post('/upload',data={'file':(io.BytesIO(raw.encode()),'test.csv')})
    wb=load_workbook(io.BytesIO(response.data))
    assert wb.sheetnames[0]=='Results'
    sheet=wb.active
    assert sheet['A8'].value=='001' and sheet['A8'].data_type=='s'
    headers=[c.value for c in sheet[7]]
    ddd=headers.index('DDD\nCPZ mg/day')+1
    assert sheet.cell(8,ddd).value==120
    assert sheet.cell(9,ddd).value=='—'
    assert sheet['B9'].value=='계산 보류'
    assert '환산계수 없음' in sheet.cell(9,len(headers)).value
    assert wb.sheetnames == ['Results','MedicationResults','Review']
    assert all(s.sheet_state == 'visible' for s in wb)
    assert wb['Results'].sheet_state=='visible'
    assert sheet.freeze_panes=='C8' and sheet.auto_filter.ref=='A7:L9'
    wb.close()


def test_dated_overview_does_not_merge_dates():
    raw='HID,PRESCR_DATE,DRUG,TABS_PER_DAY\n001,2026-09-01,Risperidone 2mg tab,1\n001,2026-09-15,Risperidone 2mg tab,2\n'
    response=app.test_client().post('/upload',data={'file':(io.BytesIO(raw.encode()),'test.csv')})
    wb=load_workbook(io.BytesIO(response.data))
    s=wb.active
    assert s.title=='Results'
    assert s['B8'].value=='2026-09-01' and s['B9'].value=='2026-09-15'
    headers=[c.value for c in s[7]]
    ddd=headers.index('DDD\nCPZ mg/day')+1
    assert s.cell(8,ddd).value==120 and s.cell(9,ddd).value==240
    assert s.freeze_panes=='D8'
    wb.close()
