"""Compact presentation layer; underlying numeric results stay unchanged."""
from collections import defaultdict
from services.result_summary import TARGETS

ORDER = ('CMD', 'DDD', 'GARDNER', 'WOODS', 'CPZ_FGA', 'MED', 'ED95', 'CMD_DIRECT', 'CMD_INDIRECT')
NAME = 'Results'


def patient_overview(rows, audits, checks):
    by_patient = defaultdict(list)
    for item in audits:
        by_patient[str(item.get('patient', ''))].append(item)
    methods = [m for m in ORDER if any(c['method'] == m for c in checks)]
    output = []
    for row in rows:
        notes = []
        for item in by_patient[str(row['patient_id'])]:
            status = item.get('status')
            if status == 'unsupported_formulation': notes.append('주사 간격·제형 확인')
            elif status == 'unknown_drug': notes.append('약물명 확인')
            elif status == 'missing_factor': notes.append('환산계수 없음')
            elif status in ('review', 'missing_unit'): notes.append('용량·단위 확인')
            if item.get('unit_assumed'): notes.append('mg 단위 가정')
            if item.get('frequency') == 'ASSUMED_QD': notes.append('1일 1회 가정')
            if item.get('route') == 'injection' and status == 'converted': notes.append('주사제 환산 가정 확인')
            if item.get('match_type') == 'user_confirmed_alias': notes.append('확인된 약어 적용')
        if 'ID 누락' in row.get('확인할 내용', ''): notes.append('환자 ID 확인')
        if not by_patient[str(row['patient_id'])]: notes.append('약물 입력 확인')
        values = {m:row.get(f'{m} ({TARGETS[m]} mg/day)') for m in methods}
        output.append(dict(id=str(row['patient_id']), values=values, notes=' · '.join(dict.fromkeys(notes))))
    return methods, output


def dated_overview(results):
    grouped = {}
    methods = [m for m in ORDER if any(r['method'] == m for r in results)]
    for result in results:
        key = (result['patient_id'], result['reference_date'])
        row = grouped.setdefault(key, dict(id=key[0], date=key[1], values={}, notes=''))
        row['values'][result['method']] = result['equivalent_mg']
        if result['status'] == 'review': row['notes'] = '상세 시트에서 미환산 사유 확인'
        elif result['status'] == 'no_record': row['notes'] = '해당 날짜의 환산 대상 처방 없음'
    return methods, list(grouped.values())


def layout(methods, rows, dated=False, date_label='처방일'):
    methods = [m for m in ORDER if m in methods]
    headers = ['환자 ID'] + ([date_label] if dated else []) + ['환산 상태'] + [m.replace('CMD_', 'CMD\n') + '\n' + TARGETS[m] + ' mg/day' for m in methods] + ['확인할 사항']
    total = len(rows)
    calculated = sum(any(v is not None for v in r['values'].values()) for r in rows)
    missing = total - calculated
    assumed = sum(bool(r['notes']) for r in rows)
    cells = [(0,0,'환자별 환산 결과' if not dated else f'환자·{date_label}별 환산 결과','title'),
             (1,0,'표시는 소수 2자리이며 원값은 보존됩니다. —는 0이 아니라 환산 불가입니다. CPZ와 OLZ 값은 서로 더하지 마세요.','subtitle'),
             (3,0,f'전체 {total}건    |    1개 이상 방법 산출 {calculated}건    |    모든 방법 보류 {missing}건    |    확인 사항 {assumed}건','card'),
             (4,0,'파랑: CPZ 기준  /  초록: OLZ 기준  ·  약물별 상세: MedicationResults  ·  확인 필요: Review','subtitle')]
    for c,h in enumerate(headers):
        style='header'
        if 'mg/day' in h: style='cpz_header' if 'CPZ' in h else 'olz_header'
        cells.append((6,c,h,style))
    for i,row in enumerate(rows,7):
        values=[row['values'].get(m) for m in methods]
        count=sum(v is not None for v in values)
        status='산출 완료' if count == len(methods) and count else '일부 산출' if count else '계산 보류'
        style='ready' if status=='산출 완료' else 'partial' if count else 'blocked'
        prefix=[row['id']]+([row['date']] if dated else [])
        for c,v in enumerate(prefix): cells.append((i,c,v,'text'))
        cells.append((i,len(prefix),status,style))
        for c,v in enumerate(values,len(prefix)+1):cells.append((i,c,'—' if v is None else v,'missing' if v is None else 'number'))
        note=row['notes'] or ('방법별 지원 범위 차이' if count and count<len(methods) else '')
        cells.append((i,len(headers)-1,note,'note'))
    widths=[18]+([14] if dated else [])+[14]+[12]*len(methods)+[34]
    return headers,cells,widths


STYLES = {
    'title':dict(size=22,color='152B46',bold=True),
    'subtitle':dict(size=11,color='52647B'),
    'card':dict(size=13,color='152B46',bold=True,bg='EAF0F8'),
    'header':dict(size=11,color='FFFFFF',bold=True,bg='243D5B'),
    'cpz_header':dict(size=10,color='FFFFFF',bold=True,bg='245B91'),
    'olz_header':dict(size=10,color='FFFFFF',bold=True,bg='227568'),
    'text':dict(size=11,color='243D5B'),
    'number':dict(size=11,color='243D5B'),
    'missing':dict(size=11,color='8390A0',bg='F1F4F7'),
    'ready':dict(size=11,color='19624E',bg='E3F3EC',bold=True),
    'partial':dict(size=11,color='815600',bg='FFF1CC',bold=True),
    'blocked':dict(size=11,color='A13A35',bg='FBE8E6',bold=True),
    'note':dict(size=10,color='52647B'),
}


def add_openpyxl(wb, methods, rows):
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    ws=wb.create_sheet(NAME,0)
    headers,cells,widths=layout(methods,rows)
    for r,c,v,kind in cells:
        cell=ws.cell(r+1,c+1,v)
        if isinstance(v,str):cell.data_type='s'
        style=STYLES[kind]
        cell.font=Font(name='맑은 고딕',size=style['size'],color=style['color'],bold=style.get('bold',False))
        bg=style.get('bg') or ('F8FAFC' if r>=7 and r%2==0 else 'FFFFFF')
        cell.fill=PatternFill('solid',fgColor=bg)
        cell.alignment=Alignment(vertical='center',horizontal='right' if kind=='number' else 'center' if kind in ('ready','partial','blocked','missing') or 'header' in kind else 'left',wrap_text=True,indent=1 if kind in ('number','note','text') else 0)
        if kind=='number':cell.number_format='0.00'
    for r in (1,2,4,5):ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=len(headers))
    for c,width in enumerate(widths,1):ws.column_dimensions[get_column_letter(c)].width=width
    for r in range(8,8+len(rows)):ws.row_dimensions[r].height=54
    for r,height in {1:38,2:30,3:10,4:34,5:30,6:10,7:56}.items():ws.row_dimensions[r].height=height
    ws.freeze_panes='C8';ws.auto_filter.ref=f'A7:{get_column_letter(len(headers))}{max(7,7+len(rows))}'
    ws.sheet_view.showGridLines=False;ws.sheet_view.zoomScale=85
    ws.sheet_properties.tabColor='245B91'
    ws.sheet_properties.pageSetUpPr.fitToPage=True
    ws.page_setup.orientation='landscape';ws.page_setup.paperSize=ws.PAPERSIZE_A3
    ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0
    ws.print_title_rows='1:7';ws.print_options.horizontalCentered=True
    wb.active=0


def add_xlsxwriter(wb, methods, rows, date_label='처방일', dated=True):
    headers,cells,widths=layout(methods,rows,dated=dated,date_label=date_label)
    ws=wb.add_worksheet(NAME)
    formats={}
    for kind,s in STYLES.items():
        formats[kind]=wb.add_format({'font_name':'맑은 고딕','font_size':s['size'],'font_color':'#'+s['color'],
            'bold':s.get('bold',False),'bg_color':'#'+s.get('bg','FFFFFF'),'valign':'vcenter','text_wrap':True,
            'align':'right' if kind=='number' else 'center' if kind in ('ready','partial','blocked','missing') or 'header' in kind else 'left',
            'indent':1 if kind in ('number','note','text') else 0,
            'num_format':'0.00' if kind=='number' else 'General'})
    for c,width in enumerate(widths):ws.set_column(c,c,width)
    for r,height in {0:38,1:30,2:10,3:34,4:30,5:10,6:56}.items():ws.set_row(r,height)
    for r in range(7,7+len(rows)):ws.set_row(r,54)
    for r,c,v,kind in cells:
        if r in (0,1,3,4):ws.merge_range(r,0,r,len(headers)-1,v,formats[kind])
        elif isinstance(v,str):ws.write_string(r,c,v,formats[kind])
        else:ws.write_number(r,c,v,formats[kind])
    ws.freeze_panes(7,3 if dated else 2);ws.autofilter(6,0,max(6,6+len(rows)),len(headers)-1)
    ws.hide_gridlines(2);ws.set_zoom(85);ws.set_tab_color('#245B91')
    ws.set_landscape();ws.set_paper(8);ws.fit_to_pages(1,0);ws.repeat_rows(0,6)
