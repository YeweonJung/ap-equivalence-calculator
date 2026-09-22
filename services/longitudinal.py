"""Date-aware prescription episodes. No fuzzy acceptance or patient persistence."""
import csv
import io
import json
import math
import re
import zipfile
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache

from services.converter import available_methods, convert_drug, normalize_target, lookup
from services.parser import dictionary_match, DOSE_RE, _dose_to_mg
from services.frames import formulation_info

RULE_VERSION = 'longitudinal-1.0'
FIELDS = {
    'patient': ['HID', 'patient_id', 'subject_id', '피험자ID', '환자ID', '연구번호'],
    'date': ['PRESCR_DATE', 'prescription_date', 'rx_date', '처방일', '처방일자'],
    'drug': ['DRUG', 'drug_name', 'medication', '약물명', '성분명'],
    'product': ['COMMERCIAL_DRUG', 'product_name', 'brand', '제품명', '상품명'],
    'daily': ['TABS_PER_DAY', 'tablets_per_day', 'daily_tablets', '일일정수', '하루정수'],
    'days': ['PRESCR_DAYS', 'days_supply', 'prescription_days', '처방일수', '투약일수'],
}
REQUIRED = ('patient', 'date', 'drug', 'daily', 'days')
TARGETS = set(lookup.source_drug)
# Explicit ingredient allow-list only. Unlisted drugs remain reviewable, not zero.
NON_TARGETS = set('escitalopram lorazepam clonazepam fluoxetine propranolol bupropion lamotrigine topiramate benproperine cetirizine benztropine lithium sertraline paroxetine fluvoxamine venlafaxine desvenlafaxine duloxetine mirtazapine trazodone alprazolam diazepam zolpidem buspirone trihexyphenidyl atenolol gabapentin pregabalin valproate carbamazepine oxcarbazepine methylphenidate atomoxetine acetaminophen ibuprofen domperidone mosapride rebamipide famotidine pantoprazole omeprazole esomeprazole magnesium melatonin'.split())


def norm(value):
    return re.sub(r'[\s_\-()]', '', str(value)).casefold()


def detect_mapping(columns):
    result = {}
    for field, aliases in FIELDS.items():
        matches = [str(c) for c in columns if norm(c) in {norm(a) for a in aliases}]
        result[field] = matches[0] if len(matches) == 1 else ''
    return result


def is_longitudinal(columns):
    # An ambiguous date mapping must never fall through to cross-date totals.
    return any(norm(c) in {norm(a) for a in FIELDS['date']} for c in columns)


def validate_mapping(columns, mapping):
    if any(not mapping.get(k) or mapping[k] not in columns for k in REQUIRED):
        raise ValueError('피험자 ID, 처방일, 약물명, 일일 정 수, 처방일수 열을 모두 연결하세요.')
    selected = [v for v in mapping.values() if v]
    if len(selected) != len(set(selected)) or any(v not in columns for v in selected):
        raise ValueError('열 연결이 중복되거나 존재하지 않는 열입니다.')


def parse_date(value):
    value = str(value).strip()
    if re.fullmatch(r'\d{8}', value):
        value = value[:4] + '-' + value[4:6] + '-' + value[6:]
    value = value.replace('/', '-').replace('.', '-')
    if not re.fullmatch(r'\d{4}-\d{1,2}-\d{1,2}', value):
        raise ValueError('날짜는 YYYY-MM-DD 형식이어야 합니다.')
    try:
        return date(*map(int, value.split('-')))
    except (ValueError, OverflowError) as exc:
        raise ValueError('유효하지 않은 날짜입니다.') from exc


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n > 0 else None
    except (ValueError, TypeError):
        return None


@lru_cache(maxsize=4096)
def medication(drug, product):
    canonical = dictionary_match(drug)
    product_canonical = dictionary_match(product) if product else None
    issues = []
    combined = drug + ' ' + product
    # Do not infer oral dosing from prescription duration for injections/liquids.
    injection = formulation_info(combined)['route'] == 'injection' or bool(re.search(r'주\s*\d|\b(?:inj|vial|amp)\b', combined, re.I))
    release = 'ER' if re.search(r'\b(?:ER|XR|SR|CR)\b|서방', drug, re.I) else 'IR'
    form = ('injection' if injection else 'oral') + ':' + release
    first = re.split(r'\s|\d', drug.strip().casefold(), maxsplit=1)[0]
    if canonical not in TARGETS:
        if product_canonical in TARGETS:
            return product_canonical, form, None, ['ingredient_conflict'], 'review'
        if first in NON_TARGETS or drug.casefold().startswith('valproic acid') or canonical in NON_TARGETS:
            return canonical or first, form, None, [], 'non_target'
        return canonical or '', form, None, ['unknown_drug'], 'review'
    if product_canonical and product_canonical != canonical:
        issues.append('ingredient_conflict')
    doses = list(DOSE_RE.finditer(drug))
    pdoses = list(DOSE_RE.finditer(product))
    strength = _dose_to_mg(float(doses[0]['dose']), doses[0]['unit']) if len(doses) == 1 else None
    if not strength or strength <= 0 or not math.isfinite(strength):
        issues.append('strength_missing')
    if product and not pdoses:
        issues.append('product_strength_missing')
    if pdoses and (len(pdoses) != 1 or strength != _dose_to_mg(float(pdoses[0]['dose']), pdoses[0]['unit'])):
        issues.append('strength_conflict')
    if injection:
        issues.append('injection_requires_review')
    elif not re.search(r'\b(?:tab|tablet|cap|capsule)s?\b|정|캡슐', drug, re.I) or re.search(r'\bml\b|액|용액|syrup|solution', combined, re.I):
        issues.append('oral_solid_unconfirmed')
    if product and (bool(re.search(r'\b(?:ER|XR|SR|CR)\b|서방', product, re.I)) != (release == 'ER')):
        issues.append('release_form_conflict')
    if re.search(r'\bPRN\b|필요시|필요\s*시|격일|\bQOD\b|taper', combined, re.I):
        issues.append('variable_schedule')
    return canonical, form, strength, issues, 'review' if issues else 'ready'


def prepare(frame, mapping, policy='review', provenance=None):
    validate_mapping(frame.columns, mapping)
    if policy not in ('review', 'replace'):
        raise ValueError('지원하지 않는 중첩 처리 규칙입니다.')
    records, seen = [], {}
    for index, row in enumerate(frame.to_dict('records')):
        if not any(str(v).strip() for v in row.values()):
            continue
        r = {k: str(row.get(mapping.get(k), '')).strip() for k in FIELDS}
        r.update(source_row=index + 2 + int(frame.attrs.get('header_row', 0)), issues=[], adjustments=[], duplicate_of='', start=None, end=None, effective_end=None, daily_mg=None)
        r['source_sheet'] = ''
        if provenance is not None:
            r['source_sheet'], r['source_row'] = provenance[index]
        # Duplicate candidates are retained and block totals, not silently deleted.
        key = tuple(str(row[c]) for c in frame.columns)
        if key in seen:
            r['duplicate_of'] = seen[key]
            r['issues'].append('duplicate_candidate')
        else:
            seen[key] = f"{r['source_sheet']}!{r['source_row']}" if r['source_sheet'] else r['source_row']
        if not r['patient']:
            r['issues'].append('missing_patient')
        try:
            r['start'] = parse_date(r['date'])
        except ValueError:
            r['issues'].append('invalid_date')
        days, daily = number(r['days']), number(r['daily'])
        if days is None or not days.is_integer() or days > 3660:
            r['issues'].append('invalid_days')
        elif r['start']:
            try:
                r['end'] = r['start'] + timedelta(days=int(days))
                r['effective_end'] = r['end']
            except OverflowError:
                r['issues'].append('invalid_days')
        name, form, strength, issues, kind = medication(r['drug'], r['product'])
        r.update(canonical=name, formulation=form, strength_mg=strength, kind=kind)
        r['issues'].extend(issues)
        if daily is None or daily > 100:
            r['issues'].append('invalid_daily_tablets')
        elif strength:
            r['daily_mg'] = strength * daily
        records.append(r)
    groups = defaultdict(list)
    for r in records:
        if r['patient'] and r['canonical'] and r['kind'] != 'non_target' and r['start']:
            groups[(r['patient'], r['canonical'], r['formulation'])].append(r)
    for items in groups.values():
        by_date = defaultdict(list)
        for r in items:
            by_date[r['start']].append(r)
        dates = sorted(by_date)
        for i, day in enumerate(dates):
            bundle = by_date[day]
            if len(bundle) > 1:
                for r in bundle:
                    r['issues'].append('same_day_multiple_orders')
            next_date = dates[i + 1] if i + 1 < len(dates) else None
            for r in bundle:
                # Even an invalid later order prevents resurrection of an older dose.
                r['next_date'] = next_date
                if policy == 'replace' and next_date and r['end'] and next_date < r['end'] and r['kind'] == 'ready' and not r['issues']:
                    r['effective_end'] = next_date
                    r['adjustments'].append('new_order_replaces_previous')
    return records


def reference_pairs(records, mode, common_date='', reference_frame=None):
    patients = sorted({r['patient'] for r in records if r['patient']})
    if mode == 'common':
        pairs = [(p, parse_date(common_date)) for p in patients]
    elif mode == 'all_dates':
        pairs = sorted({(r['patient'], r['start']) for r in records if r['patient'] and r['start']})
    elif mode == 'per_patient':
        if reference_frame is None or not {'patient_id', 'reference_date'} <= set(reference_frame.columns):
            raise ValueError('기준일 CSV에 patient_id, reference_date 열이 필요합니다.')
        pairs = []
        for row in reference_frame.to_dict('records'):
            p = str(row['patient_id']).strip()
            if not p:
                raise ValueError('기준일 파일에 빈 ID가 있습니다.')
            pairs.append((p, parse_date(row['reference_date'])))
        if len(set(pairs)) != len(pairs):
            raise ValueError('기준일 파일에 중복된 ID·날짜가 있습니다.')
    else:
        raise ValueError('기준일 모드를 확인하세요.')
    if not pairs or len(pairs) > 30000:
        raise ValueError('기준일 조합은 1~30,000개여야 합니다. 파일을 나눠 주세요.')
    return pairs


def analyze(records, pairs, methods=None, policy='review'):
    methods = methods or available_methods()
    targets = {m: normalize_target(m) for m in methods}
    by_patient = defaultdict(list)
    for r in records:
        by_patient[r['patient']].append(r)
    results, details = [], []
    conversions = {}
    for patient, day in pairs:
        relevant, blockers = [], []
        for r in by_patient[patient]:
            if r['kind'] == 'non_target':
                continue
            if r['start'] is None:
                blockers.append(r)
            elif r['start'] <= day:
                end = r['effective_end']
                if end and day < end:
                    relevant.append(r)
                elif end is None and (not r.get('next_date') or day < r['next_date']):
                    blockers.append(r)
        groups = defaultdict(list)
        for r in relevant:
            groups[r['canonical'] or r['drug']].append(r)
        ambiguous = {(r['source_sheet'], r['source_row']) for items in groups.values() if len(items) > 1 for r in items}
        selected = relevant + blockers
        if len(details) + len(selected) * len(methods) > 400000:
            raise ValueError('약물별 결과가 400,000행을 초과합니다. 기준일 또는 피험자를 나눠 주세요.')
        rows_for_method = defaultdict(list)
        for r in selected:
            reasons = list(r['issues'])
            if (r['source_sheet'], r['source_row']) in ambiguous:
                reasons.append('overlapping_orders')
            if r['kind'] != 'ready' and not reasons:
                reasons.append('unresolved_drug')
            for method in methods:
                value = None
                flags = list(dict.fromkeys(reasons))
                if not flags:
                    key = (r['canonical'], r['daily_mg'], method)
                    if key not in conversions:
                        try:
                            conversions[key] = convert_drug(*key[:2], method=method)
                        except LookupError:
                            conversions[key] = None
                    value = conversions[key]
                    if value is None:
                        flags.append('missing_factor')
                rows_for_method[method].append(value)
                details.append(dict(patient_id=patient, reference_date=day.isoformat(), source_sheet=r['source_sheet'], source_row=r['source_row'], drug=r['drug'], canonical=r['canonical'], daily_mg=r['daily_mg'], method=method, target=targets[method], equivalent_mg=value, status='review' if flags else 'calculated', reasons=';'.join(flags), adjustments=';'.join(r['adjustments'])))
        for method in methods:
            values = rows_for_method[method]
            complete = bool(values) and all(v is not None for v in values)
            results.append(dict(patient_id=patient, reference_date=day.isoformat(), method=method, target=targets[method], equivalent_mg=sum(values) if complete else None, status=('calculated_assumption' if policy == 'replace' else 'calculated') if complete else 'review' if values else 'no_record', source_rows=';'.join(f"{r['source_sheet']}!{r['source_row']}" if r['source_sheet'] else str(r['source_row']) for r in selected), rule_version=RULE_VERSION, policy=policy))
    return results, details


def safe_csv(rows, columns=None):
    out = io.StringIO(newline='')
    columns = columns or (list(rows[0]) if rows else ['status'])
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')):
                v = "'" + v
            clean[k] = '' if v is None else v
        writer.writerow(clean)
    return out.getvalue().encode('utf-8-sig')


def export_zip(records, results, details, metadata):
    audit = []
    for r in records:
        def last_day(end):
            return (end - timedelta(days=1)).isoformat() if end else ''
        audit.append(dict(patient_id=r['patient'], source_sheet=r['source_sheet'], source_row=r['source_row'], drug=r['drug'], product=r['product'], prescription_date=r['date'], days=r['days'], daily_tablets=r['daily'], canonical=r['canonical'], daily_mg=r['daily_mg'], original_end=last_day(r['end']), effective_end=last_day(r['effective_end']), kind=r['kind'], issues=';'.join(dict.fromkeys(r['issues'])), adjustments=';'.join(r['adjustments']), duplicate_of=r['duplicate_of']))
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('Results.csv', safe_csv(results))
        z.writestr('MedicationResults.csv', safe_csv(details))
        z.writestr('Audit.csv', safe_csv(audit))
        z.writestr('Review.csv', safe_csv([r for r in audit if r['issues']]))
        z.writestr('Settings.json', json.dumps(dict(rule_version=RULE_VERSION, **metadata), ensure_ascii=False, indent=2))
        from pathlib import Path
        z.writestr('README_KO.md', (Path(__file__).resolve().parents[1] / 'docs/LONGITUDINAL_KO.md').read_text(encoding='utf-8'))
    out.seek(0)
    return out
