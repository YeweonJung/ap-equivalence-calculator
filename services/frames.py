"""Medication-level records shared by the API and workbook export.

Oral records use mass units (explicit or flagged mg assumptions); depots use route-specific DDD.
"""
import re
import unicodedata
from difflib import SequenceMatcher

from services.medication_splitter import split_medication_spans
from services.parser import alias_map, dictionary_match, DOSE_RE, ORAL_CONCENTRATION_RE, parse_medication, _dose_to_mg

from services.exclusions import INGREDIENTS as EXCLUDED_INGREDIENTS, EXCLUSION_NOTE, is_excluded, CLASSES, exclusion_label, exclusion_basis, PRN_RE, PRN_BASIS, PRN_LABEL, item_exclusion_basis

NON_TARGET = CLASSES
LABELS = {
    'ready': '환산 가능', 'converted': '환산 완료', 'non_target': '항정신병약 환산 대상 아님',
    'unknown_drug': '약물 미확인', 'missing_unit': '단위 확인 필요',
    'unsupported_formulation': '제형별 환산 근거 확인 필요',
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


def _trie_pattern(words):
    """Regex equivalent to a longest-first alternation of `words`, built as a trie for speed."""
    trie = {}
    for word in words:
        node = trie
        for char in word:
            node = node.setdefault(char, {})
        node[''] = True

    def build(node):
        end = node.get('') is True
        branches = [re.escape(char) + build(child) for char, child in sorted(node.items()) if char]
        if not branches:
            return ''
        body = branches[0] if len(branches) == 1 and not end else '(?:' + '|'.join(branches) + ')'
        return body + ('?' if end else '')
    return build(trie)


# One longest-first expression preserves alias boundaries and overlap order.
_MENTION_PATTERN = re.compile(r'(?<![\w])(?:' + _trie_pattern(alias_map) + r')(?![a-z가-힣])', re.I)


def drug_mentions(text):
    hits = []
    for match in _MENTION_PATTERN.finditer(_outside(text)):
        name = alias_map.get(match.group().casefold())
        if name is None:
            # Rare Unicode IGNORECASE matches (e.g. dotted I) keep old semantics.
            name = next(name for alias, name in alias_map.items()
                        if re.fullmatch(re.escape(alias), match.group(), re.I))
        hits.append((match.start(), match.end(), name))
    return hits


def antidepressant_conflict(text, drug):
    """Do not exclude a combined or contradictory ingredient description."""
    flat = re.sub(r'[()\[\]{}（）]', ' ', text)
    mentions = drug_mentions(flat)
    names = {name for _, _, name in mentions}
    if names - {drug}:
        return True
    from services.name_supplement import near_antipsychotic
    if mentions and re.search(r'[a-z가-힣]', flat[:mentions[0][0]], re.I) and near_antipsychotic(flat[:mentions[0][0]]):
        return True  # An unknown leading drug must not be hidden by an annotation.
    allowed = {'hcl', 'hydrochloride', 'hydrobromide', 'maleate', 'succinate',
               'fumarate', 'oxalate', 'tab', 'tabs', 'tablet', 'capsule', 'cap',
               'mesylate', 'mesilate', 'besylate', 'tartrate', 'carbonate', 'citrate', 'hydrate', 'sodium',
               'potassium', 'sulfate', 'acetate', 'phosphate', 'dihydrochloride', 'monohydrate',
               'xr', 'er', 'sr', 'cr', 'ir', 'mg', 'mcg', 'ug', 'g',
               'qd', 'bid', 'tid', 'qid', 'qhs', 'q', '하루', '일', '정', '캡슐'}
    for token in re.finditer(r'(?<!\w)[A-Za-z가-힣]+\s*(?=[+-]?(?:\d|\.\d))', flat):
        word = token.group().strip().casefold()
        if not any(a <= token.start() < b for a, b, _ in mentions) and word not in allowed:
            from services.name_supplement import FORM_SUFFIX, PRODUCTS
            stem = FORM_SUFFIX.sub('', word)
            if alias_map.get(stem) != drug and PRODUCTS.get(stem) != drug and near_antipsychotic(word):
                return True  # e.g. 아티반정 = 아티반 + 정; other words that resemble no antipsychotic are notes

    # Explicit combinations with an unrecognized partner cannot become zero.
    parts = re.split(r'\s*(?:[+&/]|\bwith\b)\s*', flat, flags=re.I)
    return len(parts) > 1 and any(not drug_mentions(part) and
                                 not re.fullmatch(r'(?:day|d|일)', part.strip(), re.I)
                                 for part in parts)


def formulation_info(text):
    from services.lai_support import PRODUCT_RE
    injection = re.search(r'(?<![a-z])(?:pp[136]m|lai|depot|injection|injectable|inj|intramuscular|intravenous|subcutaneous|im|iv|sc|palmitate|decanoate|enanthate|pamoate|lauroxil)(?![a-z0-9])|주사|데포|' + PRODUCT_RE, text, re.I)
    transdermal = re.search(r'\b(?:transdermal|patch(?:es)?)\b|경피|패치|첩부', text, re.I)
    interval = re.search(r'\b(?:pp[136]m|monthly|weekly|q\d+\s*(?:w|wk|weeks?|mo|months?)|every\s+\d+\s*(?:weeks?|months?))\b|매주|매월', text, re.I)
    form = re.search(r'\b(?:pp[136]m|lai|depot|xr|er|sr|ir|tablet|capsule)\b|서방정|서방|정제|캡슐', text, re.I)
    return {'route': 'transdermal' if transdermal else 'injection' if injection else 'oral',
            'formulation': 'TRANSDERMAL' if transdermal else form.group().upper() if form else ('INJECTION' if injection else 'ORAL'),
            'interval': interval.group() if interval else ''}


def _segments(text):
    for offset, end, chunk in split_medication_spans(text):
        mentions = drug_mentions(chunk)
        from services.korean_products import PATTERN as PRODUCT_LABEL_PATTERN
        product_label = PRODUCT_LABEL_PATTERN.match(chunk)
        concentration_spans = [match.span() for match in ORAL_CONCENTRATION_RE.finditer(chunk)]
        # A name followed by a dose also marks an unknown/typo drug boundary.
        generic = list(re.finditer(r'(?<!\w)[A-Za-z가-힣][A-Za-z가-힣*]*\s*(?=[+-]?(?:\d|\.\d))', _outside(chunk)))
        # "per" is also a legacy perphenazine alias; inside a concentration
        # it belongs to the unit expression and cannot start another drug.
        starts = {start for start, _, _ in mentions
                  if not any(left <= start < right for left, right in concentration_spans)}
        for match in generic:
            if any(left <= match.start() < right for left, right in concentration_spans):
                continue
            if re.match(r'pp[136]m\b', chunk[match.start():], re.I):
                continue
            # Route + numeric frequency belongs to the preceding medication.
            # Splitting "IV 1 times a day" would discard the injection guard;
            # splitting "PO/NG 2 times a day" would discard the daily frequency.
            if match.group().strip().casefold() in {
                    'po', 'ng', 'oral', 'im', 'iv', 'sc', 'intramuscular',
                    'subcutaneous', 'intravenous', 'injectable', 'transdermal', 'patch', 'patches'}:
                continue
            if match.group().strip().casefold() not in {'lai', 'depot', 'injection', '주사', '지속형', 'q', 'every', '하루', '일', 'am', 'pm', 'qd', 'bid', 'tid', 'qid', 'qhs', 'hs', 'qam', 'mg', 'mcg', 'ug', 'g', 'tab', 'tabs', 'tablet', 'tablets', '정', '캡슐'} and not any(a <= match.start() < b for a, b, _ in mentions):
                starts.add(match.start())
        starts = sorted(starts)
        if product_label:
            starts = [start for start in starts if start == 0 or start >= product_label.end()]
        # Split only after a preceding dose: brand/generic synonyms stay together.
        cuts = [0]
        for start in starts:
            if start and re.search(r'\d', _outside(chunk[cuts[-1]:start])):
                cuts.append(start)
        for left, right in zip(cuts, cuts[1:] + [len(chunk)]):
            value = chunk[left:right].strip()
            actual = left + len(chunk[left:right]) - len(chunk[left:right].lstrip())
            yield offset + actual, offset + actual + len(value), value


_REGIMEN_RE = re.compile(r'(?<![\d.])([0-9](?:\.(?:25|5|75))?(?:\s*-\s*[0-9](?:\.(?:25|5|75))?){2,3})(?![\d.])')


def _frame(start, end, original):
    from services.korean_products import normalize_product
    normalized_product, product_note = normalize_product(original)
    text = unicodedata.normalize('NFKC', normalized_product)
    text = re.sub(r'(?<=\d),(?=\d{3}(?:,\d{3})*(?:\s*(?:mg|㎎)\b))', '', text)
    # Explicit spellings only; ambiguous units never undergo automatic fuzzy conversion.
    text = re.sub(r'(?<=\d)\s*(?:밀리그램|milligrams?|mgs)\b', 'mg', text, flags=re.I)
    if not DOSE_RE.search(text) and dictionary_match(text) not in EXCLUDED_INGREDIENTS:
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
    regimen = _REGIMEN_RE.search(_outside(text))
    if regimen and not DOSE_RE.search(text) and drug_mentions(text):
        # a-b-c without a written strength: each number is the mg taken at that time.
        head = _outside(text)[:regimen.start()]
        glued = re.search(r'(?<=[a-z가-힣])\s*(\d+(?:\.\d+)?)\s*$', head, re.I)
        if glued or not re.search(r'\d', head):
            name = text[:glued.start()] if glued else text[:regimen.start()]
            total = sum(float(v) for v in re.split(r'\s*-\s*', regimen.group(1)))
            rewritten = _frame(start, end, f"{name.rstrip()} {total:g}mg QD {text[regimen.end():].lstrip()}".strip())
            if rewritten['status'] in ('ready', 'converted'):
                basis = (f"a-b-c 해석: 약물명 뒤 숫자({glued.group(1)})는 mg 단위가 없어 함량으로 쓰지 않고, " if glued else
                         'a-b-c 해석: 함량(mg) 기재 없음 → ')
                basis += f"각 숫자를 1회 mg으로 합산 ({regimen.group(1).replace(' ', '')} → {total:g} mg/일)"
                rewritten.update(original=original, source_start=start, source_end=end, needs_review=True,
                                 frequency=regimen.group(1).replace(' ', '') + ' (mg)', regimen_basis=basis, regimen_mg_assumed=True)
                rewritten['warning'] = '; '.join(filter(None, ['확인바람: ' + basis, rewritten['warning']]))
                rewritten['calculation_note'] = '; '.join(filter(None, [basis, rewritten.get('calculation_note')]))
                return rewritten
    mentions = drug_mentions(text)
    drug = mentions[0][2] if mentions else dictionary_match(text)
    score, match_type = 100.0, 'exact'
    if not drug:
        from services.name_supplement import product_name, spelling_correction
        product = product_name(_outside(text))
        if product:
            left, right, word, stem, target = product
            named = _frame(start, end, text[:left] + target + text[right:])
            if named['drug'] == target:
                note = f'국내 제품명 (KHIDI 공개 급여목록): {word} → {target}'
                named.update(original=original, source_start=start, source_end=end, match_type='public_product_name',
                             recognized_product=stem)
                named['calculation_note'] = '; '.join(filter(None, [note, named.get('calculation_note')]))
                return named
        fix = spelling_correction(_outside(text))
        if fix:
            left, right, word, alias, target, distance, kind = fix
            corrected = _frame(start, end, text[:left] + (alias if alias in alias_map else target) + text[right:])
            if corrected['drug'] == target:
                note = {'prefix': f'약어 자동 확장 (AI 미사용): {word} → {alias}',
                        'romanized_product': f'영문 표기 ↔ 국내 제품명 음운 대응 (AI 미사용): {word} → {alias} → {target}',
                        }.get(kind, f'철자 자동 보정 (AI 미사용): {word} → {alias} ({distance}글자 차이)')
                corrected.update(original=original, source_start=start, source_end=end, needs_review=True,
                                 match_type='spelling_corrected', match_score=round(100 * (1 - distance / max(len(alias), 1)), 1),
                                 spelling_correction=f'{word} → {alias}', correction_kind=kind)
                corrected['warning'] = '; '.join(filter(None, ['확인바람: ' + note, corrected['warning']]))
                corrected['calculation_note'] = '; '.join(filter(None, [note, corrected.get('calculation_note')]))
                return corrected
        name = re.split(r'[+-]?(?:\d|\.\d)', _outside(text), maxsplit=1)[0].strip()
        score, match_type = 0.0, 'unresolved'
    info = formulation_info(text)
    frame = dict(original=original, source_start=start, source_end=end, drug=drug,
                 drug_class=NON_TARGET.get(drug, 'antipsychotic' if drug else 'unknown'),
                 dose=None, unit=None, unit_candidates='', dose_mg=None, daily_dose_mg=None,
                 frequency='', frequency_per_day=None, warning='', match_type=match_type,
                 match_score=score or 0.0, needs_review=True, **info)
    from services.lai_support import product_evidence
    frame.update(product_evidence(text))
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
        if drug in EXCLUDED_INGREDIENTS and antidepressant_conflict(text, drug):
            status = 'review'
            frame['warning'] = '배제 대상 약물과 다른 성분 또는 미확인 복합 표기가 함께 있습니다. 약물별로 분리해 주세요.'
            if len({name for _, _, name in drug_mentions(re.sub(r'[()\[\]{}（）]', ' ', text))}) > 1:
                frame['error_code'] = 'ingredient_conflict'
        else:
            status = 'non_target'
            frame['needs_review'] = match_type != 'exact'
            if drug in EXCLUDED_INGREDIENTS:
                frame['exclusion_basis'] = exclusion_basis(drug)
    elif PRN_RE.search(text):
        status = 'non_target'
        frame.update(prn_excluded=True, exclusion_basis=PRN_BASIS, needs_review=match_type != 'exact')
    elif info['route'] == 'transdermal':
        status = 'unsupported_formulation'
        frame['warning'] = '경피제·패치는 제형별 환산 근거가 없어 자동 환산하지 않습니다. 경구 용량으로 바꾸어 계산하지 마세요.'
    elif info['route'] == 'injection':
        from services.injections import injection_values
        try:
            if len(doses) != 1:
                raise ValueError('확인바람: 주사 용량을 하나로 확정할 수 없습니다.')
            frame.update(injection_values({**frame, 'original': text}))
            frame['needs_review'] |= match_type != 'exact'
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
            if regimen and frame.get('dose_mg') and frame.get('daily_dose_mg'):
                tablets = frame['daily_dose_mg'] / frame['dose_mg']
                frame['regimen_basis'] = (f"a-b-c 해석: 함량 {frame['dose_mg']:g} mg 기재 → 각 숫자를 정 수로 보고 "
                                          f"{frame['dose_mg']:g} mg × {tablets:g}정 = {frame['daily_dose_mg']:g} mg/일")
                frame['calculation_note'] = '; '.join(filter(None, [frame['regimen_basis'], frame.get('calculation_note')]))
            if text != original:
                frame['calculation_note'] = '; '.join(filter(None, [frame.get('calculation_note'), '표기 정규화 적용']))
        except ValueError as exc:
            status = 'review'
            frame['warning'] = str(exc)
    if status == 'unknown_drug' and info['route'] != 'injection':
        from services.name_supplement import UNLISTED, drug_words, near_antipsychotic
        if not near_antipsychotic(_outside(text)):
            words = drug_words(_outside(text))
            basis = (f"사전 외 약물: {' '.join(words)} — 항정신병약 사전(전 언어 성분명·RxNorm·국내 급여목록)에 없고 "
                     "항정신병약 이름과도 비슷하지 않아 비항정신병약으로 보고 0으로 계산" if words else
                     '약물명이 없는 메모 조각으로 보고 0으로 계산')
            status, drug = 'non_target', UNLISTED
            frame.update(drug=drug, drug_class='unlisted', unlisted=True, unlisted_name=' '.join(words),
                         needs_review=True, exclusion_basis=basis)
            frame['warning'] = '; '.join(filter(None, ['확인바람: ' + basis, frame['warning']]))
    if status == 'unknown_drug':
        # Parsing never performs candidate retrieval or calls an AI service.
        frame['suggestions'] = []
        frame['name_candidates'] = '[]'
    if product_note:
        frame.update({k: v for k, v in product_note.items() if k != 'calculation_note'})
        frame['calculation_note'] = '; '.join(filter(None, [product_note['calculation_note'], frame.get('calculation_note')]))
    frame.update(status=status, status_message=(PRN_LABEL + ' (환산값 0)' if frame.get('prn_excluded') else exclusion_label(drug) + ' (환산값 0)')
                 if status == 'non_target' and (drug in EXCLUDED_INGREDIENTS or frame.get('prn_excluded')) else LABELS[status])
    return frame


def parse_frames(text):
    try:
        shared_lai = bool(re.search(r'(?<![a-z])LAI\s*(?:둘\s*다|모두|both)(?![a-z])|(?:둘\s*다|모두|both)\s*LAI(?![a-z])', str(text), re.I))
        frames = []
        for start, end, value in _segments(str(text)):
            # Apply the shared route BEFORE conversion. Validate each drug's own
            # product/interval; never carry an oral daily dose into an LAI frame.
            frame = _frame(start, end, value + ' LAI' if shared_lai else value)
            if shared_lai:
                frame.update(original=value, source_start=start, source_end=end, needs_review=True)
                frame['warning'] = '; '.join(filter(None, [frame.get('warning'), '공통 LAI 표기를 각 약물에 적용']))
            frames.append(frame)
        return frames
    except ValueError as exc:
        frame = _frame(0, len(str(text)), '')
        frame.update(original=str(text), status='review', status_message=LABELS['review'], warning=str(exc))
        return [frame]


def convert_frame(frame, methods):
    from services.converter import convert_drug, normalize_target
    from services.lai_support import convert_injection, BRIDGE_LABEL
    item = dict(frame, conversions=[])
    if is_excluded(item):
        item['conversions'] = [dict(method=m, target=normalize_target(m), value=0.0, basis=item_exclusion_basis(item)) for m in methods]
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
    item['ok'] = item['status'] not in {'unknown_drug', 'review', 'missing_unit', 'unsupported_formulation', 'missing_factor'}
    if item['status'] == 'missing_factor':
        item['error'] = '선택한 환산법의 계수 또는 제형별 근거 없음: ' + ', '.join(methods)
    elif not item['ok']:
        item['error'] = item['warning'] or item['status_message']
    from services.evidence import attach_evidence
    from services.result_status import decorate
    return decorate(attach_evidence(item, methods))


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
        excluded_only = not relevant and any(is_excluded(item) for item in items)
        complete = (bool(relevant) and len(values) == len(relevant)) or excluded_only
        totals.append(dict(method=method, target_drug=target,
                           total_equivalent_dose_mg=round(math.fsum(values), 4) if complete else None,
                           partial_equivalent_dose_mg=round(math.fsum(values), 4) if values and not complete else None,
                           converted_count=len(values), unresolved_count=len(relevant)-len(values),
                           excluded_count=len(items)-len(relevant),
                           status='non_target' if excluded_only else 'complete' if complete else 'incomplete' if relevant else 'non_target',
                           needs_review=not complete or any(i['needs_review'] for i in relevant),
                           review_required=any(i.get('review_required', False) for i in items)))
    return totals
