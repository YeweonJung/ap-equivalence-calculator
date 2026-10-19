"""Local, explicitly annotated evaluation. No external model or patient storage."""
from collections import defaultdict
import math
import time
import unicodedata

VERSION = '2026.10.19-evaluation-1'
FIELDS = ('drug', 'unit', 'dose_mg', 'daily_dose_mg', 'frequency', 'route', 'active_moiety_mg', 'interval_days')
NUMERIC = {'dose_mg', 'daily_dose_mg', 'active_moiety_mg', 'interval_days'}


def unit(value):
    if value is None:
        return None
    value = unicodedata.normalize('NFKC', str(value)).casefold()
    return {'ug': 'mcg', 'μg': 'mcg'}.get(value, value)


def matches(field, actual, expected):
    if field == 'unit':
        return unit(actual) == unit(expected)
    if actual is None or expected is None:
        return actual is expected
    if field in NUMERIC:
        return (isinstance(actual, (int, float)) and isinstance(expected, (int, float))
                and math.isfinite(actual) and math.isfinite(expected)
                and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6))
    return actual == expected


def ratio(n, d):
    return n / d if d else None


def scores(tp, fp, fn):
    return dict(tp=tp, fp=fp, fn=fn, ppv=ratio(tp, tp+fp), sensitivity=ratio(tp, tp+fn),
                f1=ratio(2*tp, 2*tp+fp+fn))


def evaluate(cases, predictor=None):
    from services.frames import parse_frames, convert_frame
    from services.result_summary import METHOD_ORDER
    internal = predictor is None
    predictor = predictor or (lambda text: [convert_frame(f, METHOD_ORDER) for f in parse_frames(text)])
    details, counts = [], defaultdict(lambda: dict(tp=0, fp=0, fn=0, correct=0, n=0))
    equivalent_direction = defaultdict(lambda: dict(over=0, under=0, equal=0, missing=0))
    seen = set()
    start = time.perf_counter()
    for case in cases:
        if not isinstance(case.get('id'), str) or case['id'] in seen:
            raise ValueError('Each case requires a unique string id')
        seen.add(case['id'])
        if not isinstance(case.get('text'), str) or type(case.get('should_convert')) is not bool or not isinstance(case.get('gold'), list):
            raise ValueError('Case requires text, boolean should_convert and ordered gold list')
        if 'normal' in case and type(case['normal']) is not bool:
            raise ValueError('normal must be boolean')
        t0 = time.perf_counter()
        items = predictor(case['text'])
        elapsed = time.perf_counter() - t0
        gold = case['gold']
        exact = len(items) == len(gold)
        drug_correct = 0
        direction = dict(over=0, under=0, equal=0, missing=0, wrong_drug=0)
        for i, expected in enumerate(gold):
            actual = items[i] if i < len(items) else {}
            if 'drug' in expected and actual.get('drug') == expected['drug']:
                drug_correct += 1
            for field in FIELDS:
                if field not in expected:
                    continue  # Unannotated fields are not presumed correct/absent.
                a, e = actual.get(field), expected[field]
                good = matches(field, a, e)
                exact &= good
                c = counts[field]
                c['n'] += 1
                c['correct'] += int(good)
                c['tp'] += int(good and e is not None)
                c['fp'] += int(not good and a is not None)
                c['fn'] += int(not good and e is not None)
            for expected_conversion in expected.get('equivalents', []):
                method, target = expected_conversion['method'], expected_conversion['target']
                key = f'{method}:{target}'
                a = next((c.get('value') for c in actual.get('conversions', [])
                          if c.get('method') == method and c.get('target') == target), None)
                e = expected_conversion['value']
                good = a is e if a is None or e is None else math.isclose(a, e, abs_tol=0.00011, rel_tol=1e-6)
                exact &= good
                c = counts['equivalent:'+key]
                c['n'] += 1
                c['correct'] += int(good)
                c['tp'] += int(good and e is not None)
                c['fp'] += int(not good and a is not None)
                c['fn'] += int(not good and e is not None)
                if e is not None:
                    direction_key = 'missing' if a is None else 'equal' if good else 'over' if a > e else 'under'
                    equivalent_direction[key][direction_key] += 1
            if expected.get('daily_dose_mg') is not None:
                a, e = actual.get('daily_dose_mg'), expected['daily_dose_mg']
                if actual.get('drug') != expected.get('drug'):
                    direction['wrong_drug'] += 1
                elif a is None:
                    direction['missing'] += 1
                elif matches('daily_dose_mg', a, e):
                    direction['equal'] += 1
                elif a > e:
                    direction['over'] += 1
                else:
                    direction['under'] += 1
        # Extra frames count as additions, including their annotated field types.
        annotated = {f for g in gold for f in FIELDS if f in g}
        for extra in items[len(gold):]:
            for field in annotated:
                counts[field]['fp'] += int(extra.get(field) is not None)
        emitted = any(c.get('value') is not None for item in items for c in item.get('conversions', []))
        automatic = bool(items) and emitted and all(item.get('ok') and not item.get('needs_review', True) for item in items)
        warning = any(item.get('needs_review', True) or not item.get('ok') for item in items) or not items
        correct_output = emitted and exact and case['should_convert']
        before = case.get('before_daily_dose_mg')
        after = items[0].get('daily_dose_mg') if len(items) == 1 else None
        cleaning = None
        if isinstance(before, (int, float)) and math.isfinite(before) and isinstance(after, (int, float)) and math.isfinite(after):
            cleaning = 'unchanged' if matches('daily_dose_mg', before, after) else 'increased' if after > before else 'decreased'
        details.append(dict(id=case['id'], drug_class=case.get('drug_class', 'unannotated'),
                            route_group=case.get('route_group', 'unannotated'), should_convert=case['should_convert'],
                            normal=case.get('normal', False), emitted=emitted, automatic=automatic,
                            warning=warning, exact_fields=bool(exact), correct_output=correct_output,
                            exact_drug_list=len(items) == len(gold) and drug_correct == len(gold),
                            drug_matches=drug_correct, gold_drugs=sum('drug' in g for g in gold),
                            added_items=max(0, len(items)-len(gold)), missing_items=max(0, len(gold)-len(items)),
                            dose_direction=direction, cleaning=cleaning, elapsed_seconds=elapsed))
    def aggregate(rows):
        tp = sum(r['correct_output'] for r in rows)
        fp = sum(r['emitted'] and not r['correct_output'] for r in rows)
        fn = sum(r['should_convert'] and not r['correct_output'] for r in rows)
        normal = [r for r in rows if r['normal']]
        impossible = [r for r in rows if not r['should_convert']]
        clean = [r for r in rows if r['cleaning'] is not None]
        direction = {k: sum(r['dose_direction'][k] for r in rows) for k in ('over','under','equal','missing','wrong_drug')}
        return dict(n=len(rows), strict_output=scores(tp, fp, fn), automatic_n=sum(r['automatic'] for r in rows),
                    automatic_rate=ratio(sum(r['automatic'] for r in rows), len(rows)),
                    normal_n=len(normal), false_alert_n=sum(r['warning'] for r in normal),
                    false_alert_rate=ratio(sum(r['warning'] for r in normal), len(normal)),
                    unextractable_n=len(impossible), unsafe_emission_n=sum(r['emitted'] for r in impossible),
                    abstention_accuracy=ratio(sum(not r['emitted'] for r in impossible), len(impossible)),
                    exact_drug_accuracy=ratio(sum(r['exact_drug_list'] for r in rows), len(rows)),
                    partial_drug_matches=sum(r['drug_matches'] for r in rows), gold_drugs=sum(r['gold_drugs'] for r in rows),
                    added_items=sum(r['added_items'] for r in rows), missing_items=sum(r['missing_items'] for r in rows),
                    dose_direction=direction, dose_comparison_n=sum(direction.values()),
                    cleaning_evaluable_n=len(clean), cleaning_changed_n=sum(r['cleaning'] != 'unchanged' for r in clean),
                    cleaning_changed_rate=ratio(sum(r['cleaning'] != 'unchanged' for r in clean), len(clean)),
                    cleaning_increased_n=sum(r['cleaning']=='increased' for r in clean),
                    cleaning_decreased_n=sum(r['cleaning']=='decreased' for r in clean))
    fields = {f: dict(**scores(c['tp'],c['fp'],c['fn']), accuracy=ratio(c['correct'],c['n']),
                      correct=c['correct'], annotated_n=c['n']) for f,c in counts.items()}
    return dict(version=VERSION, overall=aggregate(details), fields=fields,
                unit_accuracy=fields.get('unit', dict(accuracy=None, annotated_n=0)),
                equivalent_direction=dict(equivalent_direction),
                by_drug_class={key:aggregate([r for r in details if r['drug_class']==key]) for key in sorted({r['drug_class'] for r in details})},
                by_route={key:aggregate([r for r in details if r['route_group']==key]) for key in sorted({r['route_group'] for r in details})},
                total_seconds=time.perf_counter()-start, external_api_cost_usd=0 if internal else None,
                cost_note='내장 규칙 파서는 외부 API 호출 0건. 하드웨어·전력·인건비는 미측정. 외부 예측의 비용은 별도 기록.',
                notes=['순서에 따른 프레임 정렬; 정렬 오류는 추가·누락 또는 요소 오답으로 계산.',
                       '오답 출력은 FP, 필요한 정답 미제공은 FN으로 함께 집계. 단위 누락 정답은 null.',
                       '단위 문자열 정확도와 mg 정규화 용량 정확도를 별도 보고.',
                       '과대·과소는 정답 대비 계산 오류이며 환자의 임상적 과다·과소투여가 아님.',
                       '합성/개발 검증을 임상 정확도·안전성·비열등성으로 해석하지 않음.'], details=details)
