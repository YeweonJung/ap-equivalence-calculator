"""Selected-base sequential estimates; pure-method exports stay intact."""
import csv
import io
import json
import math
from functools import lru_cache
from pathlib import Path
from collections import defaultdict
from itertools import groupby

from services.converter import available_targets, convert_drug, normalize_target
from services.excel_tables import write_table
from services.exclusions import is_excluded, exclusion_basis
from services.result_summary import METHOD_ORDER, TARGETS

PRIORITY = ('CMD', 'MED', 'ED95', 'DDD', 'GARDNER', 'WOODS', 'CPZ_FGA', 'CMD_DIRECT', 'CMD_INDIRECT')
POLICY_VERSION = 'selected-base-sequential-3.0'
POLICY_NOTE = ('선택한 기본 방법의 값을 유지하고, 계수가 없는 약물만 나머지 방법 순서에서 처음 계산 가능한 값으로 보완합니다. '
               '보완 순서: CMD → MED → ED95 → DDD → GARDNER → WOODS → CPZ_FGA → CMD_DIRECT → CMD_INDIRECT (기본 방법 제외). '
               '같은 기준약물로 계산한 혼합 결과이며 미환산 항목이 있으면 총합은 빈칸입니다. ' + POLICY_VERSION)
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


def resolve(frame, base, blocker='', fallback=''):
    target = normalize_target(base)
    result = dict(base=base, target=target, actual='', value=None, dose=None,
                  factor=None, source='', basis='', supplemented=False, reason='', status='미환산')
    if blocker:
        return {**result, 'reason': blocker}
    if is_excluded(frame):
        return {**result, 'value': 0.0, 'status': '대상 외', 'reason': exclusion_basis(frame['drug'])}
    if frame.get('status') not in ('ready', 'converted', 'missing_factor'):
        return {**result, 'reason': frame.get('warning') or frame.get('status_message') or '약물·용량 확인'}
    # A missing oral bridge cannot use oral factors. A separate depot-DDD case
    # remains valid when the existing injection parser validated its formulation.
    bridge_missing = frame.get('route') == 'injection' and base != 'DDD' and frame.get('oral_equivalent_mg') is None
    if bridge_missing and fallback != 'DDD':
        return {**result, 'reason': '검증된 단일 경구 대응용량 없음'}
    for method in (base,) + ((fallback,) if fallback and fallback != base else ()):
        if bridge_missing and method != 'DDD':
            continue
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
                'reason': ('단일 경구 대응용량 없음; 제형별 DDD로 보완' if bridge_missing else
                           '기본 방법 계수 없음') if fallback else ''}
    return {**result, 'reason': '적용 가능한 환산계수 없음'}


def medication_entry(frame, patient='P001', day='', blocker=''):
    return dict(frame=frame, blocker=blocker, patient_id=str(patient), date=day,
                original=frame.get('original'), drug=frame.get('drug'),
                sheet=frame.get('sheet', ''), source_row=frame.get('source_row'),
                column=frame.get('medication_column', ''), start=frame.get('source_start'),
                review_note=frame.get('warning') or '',
                note='; '.join(filter(None, [frame.get('warning'), frame.get('calculation_note')])))


def cases_for_group(entries, methods, patient='P001', day=''):
    """Keep base values; fill only missing coefficients in a fixed order."""
    def detail(entry, base, fallback=''):
        evidence = resolve(entry['frame'], base, entry['blocker'], fallback)
        return {**{k: v for k, v in entry.items() if k not in ('frame', 'blocker')},
                **evidence, 'target': TARGETS[base],
                **{method: resolve(entry['frame'], method, entry['blocker'])['value']
                   for method in METHOD_ORDER}}

    def case(base, rows):
        fallbacks = [method for method in PRIORITY if method != base
                     and any(r['actual'] == method for r in rows)]
        case_id = '+'.join([base] + fallbacks)
        values = [r['value'] for r in rows if r['value'] is not None]
        missing = len(rows) - len(values)
        complete = bool(rows) and missing == 0
        amount = round(math.fsum(values), 4) if values else None
        used = {r['actual'] for r in rows if r['actual']}
        used = [m for m in [base] + fallbacks if m in used]
        count = sum(r['supplemented'] for r in rows)
        status = ('보완 완료' if count else '원래 방법') if complete else '미완료' if rows else '처방 없음'
        return dict(patient_id=str(patient), date=day, case_id=case_id, base=base,
                    complement=' → '.join(fallbacks), target=TARGETS[base], total=amount if complete else None,
                    partial=amount if not complete else None, status=status, methods=' + '.join(used),
                    supplemented=count, missing=missing,
                    note=' · '.join(dict.fromkeys(r['review_note'] for r in rows if r['review_note'])),
                    supplement_order=[m for m in PRIORITY if m != base],
                    details=[{**r, 'case_id': case_id} for r in rows])

    for base in methods:
        original = [detail(entry, base) for entry in entries]
        unresolved = [i for i, row in enumerate(original) if row['value'] is None]
        if unresolved:
            for fallback in PRIORITY:
                if fallback == base or normalize_target(base) not in available_targets(fallback):
                    continue
                for i in unresolved:
                    candidate = detail(entries[i], base, fallback)
                    if candidate['value'] is not None:
                        original[i] = candidate
                unresolved = [i for i in unresolved if original[i]['value'] is None]
                if not unresolved:
                    break
        yield case(base, original)


def quick_cases(items, methods):
    return list(cases_for_group([medication_entry(item) for item in items], methods))


def frame_cases(audits, methods, patients):
    grouped = defaultdict(list)
    for row in audits:
        grouped[str(row['patient'])].append(medication_entry(row, row['patient']))
    for patient in patients:
        yield from cases_for_group(grouped[str(patient)], methods, patient)


def dated_cases(details, results, base_method=None):
    """Consume the original selected rows; group one patient/date at a time."""
    from services.longitudinal_excel import reason_text
    groups = {}
    for r in results:
        groups.setdefault((r['patient_id'], r['reference_date']), []).append(r['method'])
    details.seek(0)
    text = io.TextIOWrapper(details, encoding='utf-8-sig', newline='')
    try:
        batches = iter(groupby(csv.DictReader(text), key=lambda r: (r['patient_id'], r['reference_date'])))
        pending = next(batches, None)
        for (patient, day), methods in groups.items():
            entries = []
            if pending is not None and pending[0] == (patient, day):
                for _, batch in groupby(pending[1], key=lambda r: (r['source_sheet'], r['source_row'])):
                    # All methods carry the same input blockers, except missing_factor.
                    row = next(batch)
                    reasons = set(filter(None, row['reasons'].split(';'))) - {'missing_factor'}
                    frame = dict(drug=row['canonical'], original=row['drug'], daily_dose_mg=row['daily_mg'],
                                 route='oral', status='non_target' if row['status'] == 'non_target' else 'ready',
                                 sheet=row['source_sheet'], source_row=int(row['source_row']),
                                 warning=reason_text(row['adjustments'].split(';')))
                    if row.get('injection_evidence'):
                        frame.update(json.loads(row['injection_evidence']))
                    entries.append(medication_entry(frame, patient, day, reason_text(reasons)))
                pending = next(batches, None)
            yield from cases_for_group(entries, [base_method or methods[0]], patient, day)
    finally:
        text.detach()


def write_supplemented(workbook, case_factory, dated=False, date_label='처방일'):
    """Summary first, provenance second. Recompute by group to bound memory."""
    def summary():
        detail_count = 0
        for index, result in enumerate(case_factory(), 1):
            detail_count += len(result['details'])
            if index > 1048575 or detail_count > 1048575:
                raise ValueError('보완 계산안이 Excel 행 한도를 초과합니다. 환자별로 파일을 나눠 주세요.')
            yield result

    prefix = ['patient_id'] + (['date'] if dated else [])
    labels = dict(patient_id='환자 ID', date=date_label, case_id='계산안', base='기본 방법',
                  target='기준약물', total='보완 총합 (mg/day)', methods='사용 방법', complement='보완 방법',
                  status='처리', supplemented='보완 약물 수', missing='미환산 수',
                  partial='부분합 (mg/day)', note='확인할 사항')
    columns = prefix + ['case_id', 'total', 'target', 'methods', 'complement', 'status', 'missing', 'partial', 'base', 'supplemented', 'note']
    ws = write_table(workbook, '보완합계', columns, summary(), labels=labels,
                     widths=[18] + ([14] if dated else []) + [28, 20, 14, 28, 18, 16, 12, 20, 18, 14, 48],
                     number_formats={'total': '0.00', 'partial': '0.00'}, wrap_columns=('note', 'methods'))
    ws.write_comment(0, columns.index('total'), POLICY_NOTE)

    def details_rows():
        for result in case_factory():
            yield from result['details']

    labels = dict(patient_id='환자 ID', date=date_label, case_id='계산안', base='기본 방법', actual='적용 방법',
                  target='기준약물', drug='성분', dose='계산 용량 (mg/day)', factor='적용계수',
                  value='환산값 (mg/day)', status='처리', reason='사유', basis='용량 기준',
                  source='출처', original='원문 약물', sheet='원본 시트', source_row='원본 행',
                  column='원본 열', start='원문 시작위치', note='확인할 사항')
    labels.update({m: f'{m} ({TARGETS[m]} mg/day)' for m in METHOD_ORDER})
    columns = prefix + ['drug', 'actual', 'value', 'target'] + list(METHOD_ORDER) + ['status', 'base', 'dose', 'factor',
                        'reason', 'basis', 'source', 'original', 'sheet', 'source_row', 'column', 'start', 'note']
    ws = write_table(workbook, '보완근거', columns, details_rows(), labels=labels,
                     widths=[18] + ([14] if dated else []) + [22, 18, 20, 14] + [18] * len(METHOD_ORDER) + [16, 18, 20, 18, 32, 42, 65, 45, 20, 12, 20, 14, 48],
                     number_formats={c: '0.############' for c in ('dose', 'factor', 'value', *METHOD_ORDER)},
                     wrap_columns=('reason', 'basis', 'source', 'note'))
    ws.write_comment(0, columns.index('actual'), POLICY_NOTE)


def append_frame_sheets(workbook, audits, patient_rows, patient_checks, base_method=None):
    methods = [m for m in METHOD_ORDER if any(c['method'] == m for c in patient_checks)]
    patients = [r['patient_id'] for r in patient_rows]
    write_supplemented(workbook, lambda: frame_cases(audits, [base_method or (methods[0] if methods else 'CMD')], patients))


def append_dated_sheets(workbook, details, results, date_label, base_method=None):
    write_supplemented(workbook, lambda: dated_cases(details, results, base_method), dated=True, date_label=date_label)
