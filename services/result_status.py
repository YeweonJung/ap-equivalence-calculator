"""Presentation codes. These never relax a parser or a calculation blocker."""
import math

POLICY_VERSION = 'error-only-review-1.0'
LEGEND = (
    ('a', '미환산', '일부 또는 전체 방법의 환산계수·제형별 근거가 없음'),
    ('b', '인식불가', '등록된 약물명으로 인식하지 못함'),
    ('c', '정보부족', '용량·단위·빈도·주사 간격·ID 등 정보가 부족하거나 가정이 포함됨'),
    ('d', '중복·일정 불확실', '중복 의심 또는 처방 일정이 불확실함'),
    ('e', '환산대상 아님', '확인된 비대상 약물로 항정신병약 환산 기여값은 0'),
    ('x', '오류 · 검토필요', '성분·함량·단위 충돌, 잘못된 숫자·날짜 등 입력 오류'),
)
LABELS = {code: label for code, label, _ in LEGEND}
COLUMNS = ['status_code', 'status_label', 'review_required']
HEADERS = dict(status_code='상태코드', status_label='상태설명', review_required='검토필요')
CONFLICTS = {'ingredient_conflict', 'strength_conflict', 'release_form_conflict',
             'unit_conflict', 'count_conflict', 'invalid_value'}
UNCERTAIN = {'strength_missing', 'product_strength_missing', 'oral_solid_unconfirmed',
             'injection_requires_review', 'injection_quantity_ambiguous', 'missing_patient',
             'variable_schedule'}
# Only unequivocal validation failures qualify as x. Unsupported or incomplete
# information must not become an error merely because an old flag was true.
ERROR_TEXT = ('0보다 커야', '1~24회 범위', '소수·음수·0 투여간격',
              '서로 다른 복용 빈도가 함께', '성분이 서로 다릅니다',
              '성분과 제품명이 서로 다릅니다', '서로 다른 LAI 제품이 함께',
              '주사 제품명과 경구 투여 표기가 충돌',
              'LAI 투여간격과 일일 복용빈도가 함께',
              '성분 필드와 제품 필드의 주사 총용량이 다릅니다',
              '두 필드의 주사 표시량 기준이 서로 다릅니다',
              '용량 셀과 단위 열의 단위가 다릅니다', '약물·용량 개수 불일치')
UNSUPPORTED_TEXT = ('근거가 없어', '근거가 없습니다', '환산은 지원하지 않습니다',
                    '환산 대상이 아닙니다', '유지요법 DDD로 환산하지 않습니다')


def combine(*rows):
    codes = {c for row in rows for c in str(row.get('status_code', '')).split(';') if c in LABELS}
    ordered = [c for c in LABELS if c in codes]
    return dict(status_code=';'.join(ordered),
                status_label=' · '.join(f'{c}: {LABELS[c]}' for c in ordered) or '정상',
                review_required='x' in codes)


def classify(row, issues=()):
    flags = row.get('issues', ())
    if isinstance(flags, str):
        flags = flags.split(';')
    flags = set(flags or ()) | set(issues)
    if row.get('error_code'):
        flags.add(row['error_code'])
    status = row.get('status') or row.get('kind', '')
    text = ' '.join(str(row.get(k) or '') for k in ('warning', 'error', 'status_message', 'injection_error'))
    codes = set()
    if status != 'non_target' and row.get('dose') is not None:
        try:
            dose = float(row['dose'])
            if not math.isfinite(dose) or dose <= 0:
                codes.add('x')
        except (TypeError, ValueError):
            codes.add('x')
    if flags & CONFLICTS or any(s in text for s in ERROR_TEXT):
        codes.add('x')
    for flag, field in [('invalid_date', 'date'), ('invalid_days', 'days'), ('invalid_daily_tablets', 'daily')]:
        if flag not in flags:
            continue
        raw = str(row.get(field) or '').strip()
        if not raw:
            codes.add('c')
        elif flag == 'invalid_date':
            codes.add('x')
        else:
            try:
                value = float(raw)
                invalid = not math.isfinite(value) or value <= 0 or (flag == 'invalid_days' and not value.is_integer())
                codes.add('x' if invalid else 'c')  # supported-range limits are not proof of an erroneous prescription
            except (ValueError, TypeError):
                codes.add('x')
    if status == 'unknown_drug' or flags & {'unknown_drug', 'unresolved_drug'}:
        codes.add('b')
    if status == 'non_target':
        codes.add('e')
    if status == 'missing_factor' or 'missing_factor' in flags:
        codes.add('a')
    if status in ('ready', 'converted') and (row.get('unavailable_methods') or
            any(c.get('value') is None for c in row.get('conversions', ()))):
        codes.add('a')
    if 'unsupported_route' in flags or (status == 'unsupported_formulation' and any(s in text for s in UNSUPPORTED_TEXT)):
        codes.add('a')
    if flags & {'duplicate_candidate', 'same_day_multiple_orders', 'overlapping_orders'}:
        codes.add('d')
    if flags & (UNCERTAIN - {'injection_requires_review'}) or status == 'missing_unit' or row.get('unit_assumed') or row.get('frequency') == 'ASSUMED_QD':
        codes.add('c')
    if ('injection_requires_review' in flags or status in ('review', 'unsupported_formulation')) and not codes & {'a', 'b', 'x'}:
        codes.add('c')
    if 'ID 누락' in text or '약물 열을 찾지 못' in text or str(row.get('patient', '')).startswith('__MISSING_ID_'):
        codes.add('c')
    if not codes and row.get('needs_review') and row.get('warning') and row.get('match_type') != 'user_confirmed_alias':
        codes.add('c')
    return combine(dict(status_code=';'.join(codes)))


def decorate(row, issues=()):
    return {**row, **classify(row, issues)}


def display_value(value, column):
    """Render review flags without changing the boolean used by calculation logic."""
    if column in ('review_required', '검토필요') and isinstance(value, bool):
        return 'yes' if value else 'no'
    return value


def add_legend(workbook):
    from services.excel_tables import write_table
    rows = [dict(code=c, label=l, description=d, review='검토필요' if c == 'x' else '해당 없음') for c, l, d in LEGEND]
    rows.append(dict(code='공통', label='빈칸은 0이 아님', description='미환산 항목이 있는 방법의 전체 합계는 비워 둡니다. 부분합은 별도로 표시합니다. 코드가 없으면 정상이며, 여러 상태는 ;로 함께 표시합니다.', review='Review 시트에는 x만 수록'))
    write_table(workbook, '코드안내', ['code', 'label', 'description', 'review'], rows,
                labels=dict(code='코드', label='뜻', description='설명', review='검토필요 여부'),
                widths=[12, 24, 80, 28], wrap_columns=('description', 'label', 'review'))
