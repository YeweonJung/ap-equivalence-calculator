"""Separate, traceable mixed-method estimates; pure-method exports stay intact."""
import csv
import io
import math
from functools import lru_cache
from pathlib import Path

from services.converter import available_targets, convert_drug, normalize_target
from services.excel_tables import write_table
from services.exclusions import is_excluded, exclusion_basis
from services.result_summary import METHOD_ORDER, TARGETS

PRIORITY = ('CMD', 'MED', 'ED95', 'DDD', 'GARDNER', 'WOODS', 'CPZ_FGA', 'CMD_DIRECT', 'CMD_INDIRECT')
POLICY_VERSION = 'supplemented-1.0'
POLICY_NOTE = ('기본 방법 우선. 계수 부재만 CMD → MED → ED95 → DDD → GARDNER → WOODS → '
               'CPZ_FGA → CMD_DIRECT → CMD_INDIRECT 순서로 보완. 같은 기준약물로 계산한 혼합 결과이며, '
               '단일 환산법의 결과가 아닙니다. 미환산 항목이 있으면 총합은 빈칸입니다. ' + POLICY_VERSION)
SOURCES = {
    'CMD': 'https://pubmed.ncbi.nlm.nih.gov/25841041/',
    'MED': 'https://pubmed.ncbi.nlm.nih.gov/24493852/',
    'ED95': 'https://pubmed.ncbi.nlm.nih.gov/31838873/',
    'DDD': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4960429/',
    'CPZ_FGA': 'https://pubmed.ncbi.nlm.nih.gov/4156792/',
}
with (Path(__file__).resolve().parents[1] / 'lookup/equivalence_anchors.csv').open(encoding='utf-8') as stream:
    ANCHORS = {(r['method_id'], r['drug']): r for r in csv.DictReader(stream)}


@lru_cache(maxsize=None)
def source_for(method, drug, target):
    rows = [ANCHORS[method, d] for d in (drug, target) if (method, d) in ANCHORS]
    return '; '.join(dict.fromkeys(
        f"{r['source']} [{r['table']}; {r['version']}]" for r in rows)) or SOURCES.get(method, '')


def convert_with_evidence(frame, method, target):
    """Return an unrounded value and the dose/factor actually multiplied."""
    if target not in available_targets(method):
        raise LookupError('같은 기준약물의 계수 없음')
    drug = frame.get('drug')
    basis, source = '경구 일일용량', source_for(method, drug, target)
    if frame.get('route') == 'injection':
        from services.lai_support import convert_injection
        value = convert_injection(frame, method, target)
        if method == 'DDD':
            dose = frame['daily_dose_mg']
            basis = '주사 활성성분 일일량 / 제형별 DDD × 기준약물 DDD'
            from services.injections import CPZ_SOURCE
            source = '; '.join(filter(None, [frame.get('conversion_source'), CPZ_SOURCE,
                                             source_for('DDD', 'chlorpromazine', target), frame.get('mass_source')]))
        else:
            dose = frame['oral_equivalent_mg']
            basis = '제품별 경구 대응 일일용량'
            source = '; '.join(filter(None, [source, frame.get('oral_bridge_source'), frame.get('mass_source')]))
        factor = value / dose
    else:
        dose = frame.get('daily_dose_mg')
        value = convert_drug(drug, dose, method, target)
        dose = float(dose)
        factor = convert_drug(drug, 1, method, target)
    return dict(value=value, dose=dose, factor=factor, basis=basis, source=source)


def resolve(frame, base, blocker=''):
    target = normalize_target(base)
    result = dict(base=base, target=target, actual='', value=None, dose=None,
                  factor=None, source='', basis='', supplemented=False, reason='', status='미환산')
    if blocker:
        return {**result, 'reason': blocker}
    if is_excluded(frame):
        return {**result, 'value': 0.0, 'status': '대상 외', 'reason': exclusion_basis(frame['drug'])}
    if frame.get('status') not in ('ready', 'converted', 'missing_factor'):
        return {**result, 'reason': frame.get('warning') or frame.get('status_message') or '약물·용량 확인'}
    # Missing oral correspondence is a formulation problem, not a missing factor.
    if frame.get('route') == 'injection' and base != 'DDD' and frame.get('oral_equivalent_mg') is None:
        return {**result, 'reason': '검증된 단일 경구 대응용량 없음'}
    for method in (base,) + tuple(m for m in PRIORITY if m != base):
        try:
            evidence = convert_with_evidence(frame, method, target)
        except LookupError:
            if frame.get('unit_assumed'):
                return {**result, 'reason': '용량 단위 확인 후 보완 가능'}
            continue
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            return {**result, 'reason': '용량·제형 정보 확인'}
        fallback = method != base
        return {**result, **evidence, 'actual': method, 'supplemented': fallback,
                'status': '보완' if fallback else '원래 방법',
                'reason': '기본 방법 계수 없음' if fallback else ''}
    return {**result, 'reason': '적용 가능한 환산계수 없음'}


def frame_rows(audits, methods):
    for row in audits:
        for base in methods:
            result = resolve(row, base)
            yield dict(patient_id=str(row['patient']), date='', original=row.get('original'),
                       drug=row.get('drug'), sheet=row.get('sheet'), source_row=row.get('source_row'),
                       column=row.get('medication_column'), start=row.get('source_start'),
                       note=row.get('warning', ''), **{**result, 'target': TARGETS[base]})


def dated_rows(details):
    """Reuse exactly the selected patient/date rows and their original blockers."""
    from services.longitudinal_excel import reason_text
    details.seek(0)
    text = io.TextIOWrapper(details, encoding='utf-8-sig', newline='')
    try:
        for row in csv.DictReader(text):
            reasons = set(filter(None, row['reasons'].split(';'))) - {'missing_factor'}
            frame = dict(drug=row['canonical'], daily_dose_mg=row['daily_mg'], route='oral',
                         status='non_target' if row['status'] == 'non_target' else 'ready')
            result = resolve(frame, row['method'], reason_text(reasons))
            yield dict(patient_id=row['patient_id'], date=row['reference_date'], original=row['drug'],
                       drug=row['canonical'], sheet=row['source_sheet'], source_row=int(row['source_row']),
                       column='', start=None, note=reason_text(row['adjustments'].split(';')),
                       **{**result, 'target': TARGETS[row['method']]})
    finally:
        text.detach()


def write_supplemented(workbook, row_factory, groups, dated=False, date_label='처방일'):
    """Two streaming passes keep large exports bounded and source rows auditable."""
    totals = {key: dict(values=[], missing=0, count=0, supplements=0, methods=[], notes=[])
              for key in groups}
    for row in row_factory():
        key = (row['patient_id'], row['date'], row['base'])
        total = totals[key]
        total['count'] += 1
        if row['value'] is None:
            total['missing'] += 1
        else:
            total['values'].append(row['value'])
        total['supplements'] += int(row['supplemented'])
        if row['actual'] and row['actual'] not in total['methods']:
            total['methods'].append(row['actual'])
        if row['note'] and row['note'] not in total['notes']:
            total['notes'].append(row['note'])

    def summary():
        for (patient, day, base), total in totals.items():
            complete = total['count'] > 0 and total['missing'] == 0
            value = math.fsum(total['values']) if total['values'] else None
            status = ('보완 완료' if total['supplements'] else '원래 방법') if complete else '미완료' if total['count'] else '처방 없음'
            yield dict(patient_id=patient, date=day, base=base, target=TARGETS[base],
                       total=round(value, 4) if complete else None,
                       partial=round(value, 4) if not complete and value is not None else None,
                       status=status, supplemented=total['supplements'], missing=total['missing'],
                       methods=' + '.join(total['methods']),
                       note=' · '.join(total['notes']))

    labels = dict(patient_id='환자 ID', date=date_label, base='기본 방법', target='기준약물',
                  total='보완 총합 (mg/day)', partial='부분합 (mg/day)', status='처리',
                  supplemented='보완 약물 수', missing='미환산 수', methods='사용 방법', note='확인할 사항')
    prefix = ['patient_id'] + (['date'] if dated else [])
    columns = prefix + ['base', 'target', 'total', 'status', 'supplemented', 'missing', 'partial', 'methods', 'note']
    ws = write_table(workbook, '보완합계', columns, summary(), labels=labels,
                     widths=[18] + ([14] if dated else []) + [18, 14, 20, 16, 14, 12, 20, 30, 48],
                     number_formats={'total': '0.00', 'partial': '0.00'}, wrap_columns=('note', 'methods'))
    ws.write_comment(0, columns.index('total'), POLICY_NOTE)

    labels = dict(patient_id='환자 ID', date=date_label, base='기본 방법', actual='적용 방법',
                  target='기준약물', drug='성분', dose='계산 용량 (mg/day)', factor='적용계수',
                  value='환산값 (mg/day)', status='처리', reason='사유', basis='용량 기준',
                  source='출처', original='원문 약물', sheet='원본 시트', source_row='원본 행',
                  column='원본 열', start='원문 시작위치', note='확인할 사항')
    columns = prefix + ['base', 'drug', 'actual', 'target', 'dose', 'factor', 'value', 'status',
                        'reason', 'basis', 'source', 'original', 'sheet', 'source_row', 'column', 'start', 'note']
    ws = write_table(workbook, '보완근거', columns, row_factory(), labels=labels,
                     widths=[18] + ([14] if dated else []) + [18, 22, 18, 14, 20, 18, 20, 16, 32, 42, 65, 45, 20, 12, 20, 14, 48],
                     number_formats={c: '0.############' for c in ('dose', 'factor', 'value')},
                     wrap_columns=('reason', 'basis', 'source', 'note'))
    ws.write_comment(0, columns.index('actual'), POLICY_NOTE)


def append_frame_sheets(workbook, audits, patient_rows, patient_checks):
    methods = [m for m in METHOD_ORDER if any(c['method'] == m for c in patient_checks)]
    groups = [(str(r['patient_id']), '', m) for r in patient_rows for m in methods]
    write_supplemented(workbook, lambda: frame_rows(audits, methods), groups)


def append_dated_sheets(workbook, details, results, date_label):
    groups = [(r['patient_id'], r['reference_date'], r['method']) for r in results]
    write_supplemented(workbook, lambda: dated_rows(details), groups, dated=True, date_label=date_label)
