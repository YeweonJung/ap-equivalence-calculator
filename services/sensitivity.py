"""Coverage and paired comparisons of pure methods on a common native scale."""
from collections import defaultdict
from itertools import combinations
from statistics import mean, median
import math

from services.converter import DEFAULT_TARGETS
from services.excel_tables import write_table

VERSION = '2026.10.19-sensitivity-1'
NOTE = ('순수 방법만 비교. 검토 필요·미환산·대상 외 전용 행은 공통 분석집단에서 제외. '
        '동일 기준약물인 방법끼리만 수치 비교. 상관은 일치도·임상적 동등성의 증명이 아님. '
        '환자-처방일 자료의 반복측정을 독립 표본으로 간주한 추론검정은 제공하지 않음.')


def frame_observations(checks, blocked_patients=()):
    return [dict(patient_id=str(r['patient_id']), date='', method=r['method'],
                 value=r['total_equivalent_dose_mg'], review=r['needs_review'] or r['patient_id'] in blocked_patients,
                 excluded=r['status'] == 'non_target', status=r['status']) for r in checks]


def dated_observations(results):
    return [dict(patient_id=str(r['patient_id']), date=r['reference_date'], method=r['method'],
                 value=r['equivalent_mg'], review=r['status'] not in ('calculated', 'non_target'),
                 excluded=r['status'] == 'non_target', status=r['status']) for r in results]


def summarize(observations):
    data, units = {}, set()
    for r in observations:
        unit = (r['patient_id'], r['date'])
        key = (*unit, r['method'])
        if key in data:
            raise ValueError('Duplicate patient/date/method in sensitivity input')
        if r['method'] not in DEFAULT_TARGETS:
            raise ValueError('Unknown method in sensitivity input')
        data[key] = r
        units.add(unit)
    methods = [m for m in DEFAULT_TARGETS if any(k[2] == m for k in data)]
    eligible, numeric = defaultdict(set), defaultdict(set)
    eligibility = []
    for unit in sorted(units):
        for method in methods:
            r = data.get((*unit, method), {})
            value = r.get('value')
            present = isinstance(value, (int, float)) and math.isfinite(value)
            if present:
                numeric[method].add(unit)
            ok = present and not r.get('review', True) and not r.get('excluded', False)
            if ok:
                eligible[method].add(unit)
            eligibility.append(dict(patient_id=unit[0], date=unit[1], method=method,
                                    target=DEFAULT_TARGETS[method], value=value, eligible=ok,
                                    reason='공통집단 후보' if ok else '대상 외 약물만 있음' if r.get('excluded') else
                                    '검토 필요' if present else '미환산 또는 해당 처방 없음'))
    by_target = defaultdict(list)
    for method in methods:
        by_target[DEFAULT_TARGETS[method]].append(method)
    common = {target: set.intersection(*(eligible[m] for m in group)) for target, group in by_target.items()}
    coverage = []
    for method in methods:
        target = DEFAULT_TARGETS[method]
        selected = eligible[method]
        values = [data[(*u, method)]['value'] for u in selected]
        shared = [data[(*u, method)]['value'] for u in common[target]]
        excluded = sum(r.get('excluded', False) for k, r in data.items() if k[2] == method)
        coverage.append(dict(method=method, target=target, denominator=len(units),
                             unique_patients=len({u[0] for u in units}), numeric_n=len(numeric[method]),
                             eligible_n=len(selected), coverage=len(selected)/len(units) if units else None,
                             non_target_n=excluded, review_or_missing_n=len(units)-len(selected)-excluded,
                             mean=mean(values) if values else None, median=median(values) if values else None,
                             common_methods=', '.join(by_target[target]), common_n=len(shared),
                             common_mean=mean(shared) if shared else None, note=NOTE))
    comparisons = []
    for left, right in combinations(methods, 2):
        same = DEFAULT_TARGETS[left] == DEFAULT_TARGETS[right]
        paired = sorted(eligible[left] & eligible[right]) if same else []
        x = [data[(*u, left)]['value'] for u in paired]
        y = [data[(*u, right)]['value'] for u in paired]
        delta = [b-a for a,b in zip(x,y)]
        correlation = None
        if len(x) >= 3 and len(set(x)) > 1 and len(set(y)) > 1:
            import pandas as pd
            correlation = float(pd.Series(x).rank().corr(pd.Series(y).rank()))
        comparisons.append(dict(left=left, right=right, target=DEFAULT_TARGETS[left] if same else '',
                                paired_n=len(paired) if same else None,
                                mean_difference=mean(delta) if delta else None,
                                median_absolute_difference=median([abs(d) for d in delta]) if delta else None,
                                spearman=correlation,
                                note='차이 = 오른쪽 방법 − 왼쪽 방법. ' + NOTE if same else '기준약물이 달라 수치 비교하지 않음'))
    return dict(version=VERSION, coverage=coverage, comparisons=comparisons, eligibility=eligibility)


def append_sheets(workbook, observations):
    report = summarize(observations)
    definitions = [
        ('MethodCoverage', 'coverage', ['method', 'target', 'denominator', 'unique_patients', 'numeric_n', 'eligible_n', 'coverage', 'non_target_n', 'review_or_missing_n', 'mean', 'median', 'common_methods', 'common_n', 'common_mean', 'note']),
        ('MethodComparison', 'comparisons', ['left', 'right', 'target', 'paired_n', 'mean_difference', 'median_absolute_difference', 'spearman', 'note']),
        ('MethodEligibility', 'eligibility', ['patient_id', 'date', 'method', 'target', 'value', 'eligible', 'reason']),
    ]
    labels = dict(method='환산 방법', target='기준약물 (mg/day)', denominator='전체 환자·날짜 수', unique_patients='고유 환자 수',
                  numeric_n='숫자 산출 수', eligible_n='검토 불필요 완전합계 수', coverage='분석 가능 비율',
                  non_target_n='대상 외 전용 수', review_or_missing_n='검토·미환산 수', mean='방법별 가능집단 평균',
                  median='방법별 가능집단 중앙값', common_methods='같은 척도의 비교 방법', common_n='전체 비교 방법 공통 수',
                  common_mean='공통집단 평균', note='해석 기준', left='왼쪽 방법', right='오른쪽 방법',
                  paired_n='두 방법 공통 수', mean_difference='평균 차이 (오른쪽-왼쪽)',
                  median_absolute_difference='절대차 중앙값', spearman='순위상관', patient_id='환자 ID',
                  date='처방일', value='순수 방법 총합 (mg/day)', eligible='분석 포함', reason='포함·제외 사유')
    for name, key, columns in definitions:
        write_table(workbook, name, columns, report[key], labels=labels, wrap_columns=('note', 'reason'),
                    number_formats={'coverage': '0.0%', 'spearman': '0.0000'})
    from services.evidence import method_info
    write_table(workbook, 'MethodInfo', ['method', 'evidence_type', 'source', 'publication_year',
                                       'evidence_grade', 'grade_note', 'limitation', 'common_limit'], method_info(),
                wrap_columns=('grade_note', 'limitation', 'common_limit', 'source'))
