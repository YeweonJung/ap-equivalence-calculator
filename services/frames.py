"""Medication-level records shared by the API and workbook export.

Oral records use mass units (explicit or flagged mg assumptions); depots use route-specific DDD.
"""
import re
import unicodedata
from difflib import SequenceMatcher

from services.medication_splitter import split_medication_spans
from services.parser import alias_map, dictionary_match, DOSE_RE, parse_medication, _dose_to_mg

NON_TARGET = {'escitalopram': 'antidepressant', 'benztropine': 'anticholinergic', 'lithium': 'mood_stabilizer'}
LABELS = {
    'ready': '환산 가능', 'converted': '환산 완료', 'non_target': '항정신병약 환산 대상 아님',
    'unknown_drug': '약물 미확인', 'missing_unit': '단위 확인 필요',
    'unsupported_formulation': '주사제 제형별 환산 근거 확인 필요',
    'missing_factor': '해당 환산법의 계수 없음', 'review': '입력 확인 필요',
}


def _outside(text):
    depth, chars = 0, []
    for char in text:
        if char in '([{（':
            depth += 1
        chars.append(' ' if depth else char)
        if char in ')]}）':
            depth = max(0, depth - 1)
    return ''.join(chars)


def drug_mentions(text):
    masked = _outside(text)
    hits = []
    for alias, name in alias_map.items():
        pattern = r'(?<![\w])' + re.escape(alias) + r'(?![a-z가-힣])'
        for match in re.finditer(pattern, masked, re.I):
            hits.append((match.start(), match.end(), name))
    chosen = []
    for hit in sorted(hits, key=lambda x: (x[0], -(x[1]-x[0]))):
        if not chosen or hit[0] >= chosen[-1][1]:
            chosen.append(hit)
    return chosen


def formulation_info(text):
    from services.lai_support import PRODUCT_RE
    injection = re.search(r'(?<![a-z])(?:pp[136]m|lai|depot|injection|injectable|intramuscular|subcutaneous|im|iv|sc)(?![a-z0-9])|주사|데포|' + PRODUCT_RE, text, re.I)
    interval = re.search(r'\b(?:pp[136]m|monthly|weekly|q\d+\s*(?:w|wk|weeks?|mo|months?)|every\s+\d+\s*(?:weeks?|months?))\b|매주|매월', text, re.I)
    form = re.search(r'\b(?:pp[136]m|lai|depot|xr|er|sr|ir|tablet|capsule)\b|서방정|서방|정제|캡슐', text, re.I)
    return {'route': 'injection' if injection else 'oral',
            'formulation': form.group().upper() if form else ('INJECTION' if injection else 'UNSPECIFIED'),
            'interval': interval.group() if interval else ''}


def _segments(text):
    for offset, end, chunk in split_medication_spans(text):
        mentions = drug_mentions(chunk)
        # A name followed by a dose also marks an unknown/typo drug boundary.
        generic = list(re.finditer(r'(?<!\w)[A-Za-z가-힣][A-Za-z가-힣*]*\s*(?=[+-]?(?:\d|\.\d))', _outside(chunk)))
        starts = {start for start, _, _ in mentions}
        for match in generic:
            if re.match(r'pp[136]m\b', chunk[match.start():], re.I):
                continue
            if match.group().strip().casefold() not in {'lai', 'depot', 'injection', '주사', '지속형', 'q', 'every', '하루', '일', 'am', 'pm', 'qd', 'bid', 'tid', 'qid', 'qhs', 'hs', 'qam', 'mg', 'mcg', 'ug', 'g', 'tab', 'tabs', 'tablet', 'tablets', '정', '캡슐'} and not any(a <= match.start() < b for a, b, _ in mentions):
                starts.add(match.start())
        starts = sorted(starts)
        # Split only after a preceding dose: brand/generic synonyms stay together.
        cuts = [0]
        for start in starts:
            if start and re.search(r'\d', _outside(chunk[cuts[-1]:start])):
                cuts.append(start)
        for left, right in zip(cuts, cuts[1:] + [len(chunk)]):
            value = chunk[left:right].strip()
            actual = left + len(chunk[left:right]) - len(chunk[left:right].lstrip())
            yield offset + actual, offset + actual + len(value), value


def _frame(start, end, original):
    text = unicodedata.normalize('NFKC', original)
    text = re.sub(r'(?<=\d),(?=\d{3}(?:,\d{3})*(?:\s*(?:mg|㎎)\b))', '', text)
    # Explicit spellings only; ambiguous units never undergo automatic fuzzy conversion.
    text = re.sub(r'(?<=\d)\s*(?:밀리그램|milligrams?|mgs)\b', 'mg', text, flags=re.I)
    if not DOSE_RE.search(text):
        bare = re.search(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)', _outside(text))
        if bare:
            tail = text[bare.end():].strip()
            allowed = not tail or tail.startswith(('(', '[', '（')) or bool(re.fullmatch(r'(?:QD|BID|TID|QID|QHS|HS|QAM|QOD|daily|매일|1일\s*[1-4]회)', tail, re.I))
            if formulation_info(text)['route'] == 'injection' and re.match(r'(?:LAI|PP[136]M|depot|주사|지속형)(?![a-z])', tail, re.I):
                allowed = True
            if allowed:
                assumed = _frame(start, end, text[:bare.end()] + 'mg' + text[bare.end():])
                assumed.update(original=original, source_start=start, source_end=end, unit_assumed=True, needs_review=True)
                assumed['warning'] = '; '.join(filter(None, ['확인바람: 단위 미기재로 mg 가정', assumed['warning']]))
                return assumed
    mentions = drug_mentions(text)
    drug = mentions[0][2] if mentions else dictionary_match(text)
    score, match_type = 100.0, 'exact'
    if not drug:
        name = re.split(r'[+-]?(?:\d|\.\d)', _outside(text), maxsplit=1)[0].strip()
        score, match_type = 0.0, 'unresolved'
    info = formulation_info(text)
    frame = dict(original=original, source_start=start, source_end=end, drug=drug,
                 drug_class=NON_TARGET.get(drug, 'antipsychotic' if drug else 'unknown'),
                 dose=None, unit=None, unit_candidates='', dose_mg=None, daily_dose_mg=None,
                 frequency='', frequency_per_day=None, warning='', match_type=match_type,
                 match_score=score or 0.0, needs_review=True, **info)
    doses = list(DOSE_RE.finditer(text))
    if len(doses) == 1:
        frame.update(dose=float(doses[0]['dose']), unit=doses[0]['unit'],
                     dose_mg=_dose_to_mg(float(doses[0]['dose']), doses[0]['unit']))
    elif not doses:
        bare = re.search(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)', _outside(text))
        if bare:
            frame['dose'] = float(bare.group())
            unit_match = re.match(r'\s*([a-zμ]+)', _outside(text)[bare.end():], re.I)
            if unit_match and unit_match[1].casefold() not in {'qd', 'bid', 'tid', 'qid', 'qhs', 'hs', 'qam'}:
                frame['unit'] = unit_match[1]
                candidates = [unit for unit in ('mg', 'mcg', 'ug', 'g')
                              if SequenceMatcher(None, unit_match[1].casefold(), unit).ratio() >= .5]
                frame['unit_candidates'] = ', '.join(candidates)
    status = 'ready'
    if not drug:
        status = 'unknown_drug'
    elif drug in NON_TARGET:
        status = 'non_target'
        frame['needs_review'] = match_type != 'exact'
    elif info['route'] == 'injection':
        from services.injections import injection_values
        try:
            if len(doses) != 1:
                raise ValueError('확인바람: 주사 용량을 하나로 확정할 수 없습니다.')
            frame.update(injection_values(frame))
        except ValueError as exc:
            status = 'unsupported_formulation'
            frame['warning'] = str(exc)
    elif not doses and frame['dose'] is not None:
        status = 'missing_unit'
        if frame['unit_candidates']:
            frame['warning'] = '단위 후보: ' + frame['unit_candidates'] + ' (자동 적용하지 않음)'
    else:
        try:
            # Canonical drug + its own suffix prevents unrelated annotations from
            # influencing dictionary matching. Retain schedule/formulation text.
            parsed = parse_medication(text if match_type == 'exact' else drug + ' ' + text[len(name):].lstrip())
            frame.update({key: value for key, value in parsed.items() if key not in {'original','match_type','match_score'}})
            frame['needs_review'] |= match_type != 'exact'
            if text != original:
                frame['warning'] = '; '.join(filter(None, [frame['warning'], '표기 정규화 적용']))
                frame['needs_review'] = True
        except ValueError as exc:
            status = 'review'
            frame['warning'] = str(exc)
    if status == 'unknown_drug':
        import json
        from services.drug_suggestions import suggest_drugs
        frame['suggestions'] = suggest_drugs(original)
        frame['name_candidates'] = json.dumps(frame['suggestions'], ensure_ascii=False)
    frame.update(status=status, status_message=LABELS[status])
    return frame


def parse_frames(text):
    try:
        frames = [_frame(start, end, value) for start, end, value in _segments(str(text))]
        if re.search(r'(?<![a-z])LAI\s*(?:둘\s*다|모두|both)(?![a-z])|(?:둘\s*다|모두|both)\s*LAI(?![a-z])', str(text), re.I):
            for frame in frames:
                frame.update(route='injection', formulation='LAI', status='unsupported_formulation',
                             status_message=LABELS['unsupported_formulation'], daily_dose_mg=None,
                             warning='확인바람: 공통 LAI 표기. 각 약물의 제형과 투여간격을 명시해 주세요.', needs_review=True)
                frame.pop('injection_cpz_ddd', None)
        return frames
    except ValueError as exc:
        frame = _frame(0, len(str(text)), '')
        frame.update(original=str(text), status='review', status_message=LABELS['review'], warning=str(exc))
        return [frame]


def convert_frame(frame, methods):
    from services.converter import convert_drug, normalize_target
    from services.lai_support import convert_injection, BRIDGE_LABEL
    item = dict(frame, conversions=[])
    if item['status'] == 'ready':
        for method in methods:
            target = normalize_target(method)
            try:
                if item['route'] == 'injection':
                    value = round(convert_injection(item, method, target), 4)
                else:
                    value = round(convert_drug(item['drug'], item['daily_dose_mg'], method, target), 4)
            except LookupError:
                value = None
            basis = BRIDGE_LABEL if item['route'] == 'injection' and method != 'DDD' and value is not None else 'WHO depot DDD' if item['route'] == 'injection' and method == 'DDD' else ''
            item['conversions'].append(dict(method=method, target=target, value=value, basis=basis))
        item['status'] = 'converted' if any(c['value'] is not None for c in item['conversions']) else 'missing_factor'
        item['status_message'] = LABELS[item['status']]
    item['ok'] = item['status'] not in {'unknown_drug', 'review', 'missing_unit', 'unsupported_formulation'}
    if not item['ok']:
        item['error'] = item['warning'] or item['status_message']
    return item


def summarize_frames(items, methods):
    """Sum within a single source cell, separately by method and target."""
    import math
    from services.converter import normalize_target, convert_drug
    from services.lai_support import convert_injection
    totals = []
    relevant = [item for item in items if item['status'] != 'non_target']
    for method in methods:
        target = normalize_target(method)
        values = []
        for item in relevant:
            conversion = next((c for c in item['conversions'] if c['method'] == method and c['target'] == target), None)
            if conversion and conversion['value'] is not None:
                values.append(convert_injection(item, method, target) if item['route'] == 'injection' else convert_drug(item['drug'], item['daily_dose_mg'], method, target))
        complete = bool(relevant) and len(values) == len(relevant)
        totals.append(dict(method=method, target_drug=target,
                           total_equivalent_dose_mg=round(math.fsum(values), 4) if complete else None,
                           partial_equivalent_dose_mg=round(math.fsum(values), 4) if values and not complete else None,
                           converted_count=len(values), unresolved_count=len(relevant)-len(values),
                           excluded_count=len(items)-len(relevant),
                           status='complete' if complete else 'incomplete' if relevant else 'non_target',
                           needs_review=not complete or any(i['needs_review'] for i in relevant)))
    return totals
