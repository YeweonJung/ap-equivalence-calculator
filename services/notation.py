"""Rewrite common prescription notations into the forms the parser reads (no AI).

Applied to one medication segment after NFKC normalization. Every rule is idempotent and only
rewrites patterns whose meaning is standard; ambiguous forms (ranges, '#n' without a tablet count)
are left alone so the parser keeps holding them. Returns (text, notes); a note is shown to the user
whenever the rewrite interprets rather than just respells (slot doses, solution volume).
"""
import re

FREQ_WORD = {1: 'qd', 2: 'bid', 3: 'tid', 4: 'qid'}
KO_NUM = {'한': 1, '두': 2, '세': 3, '네': 4, '1': 1, '2': 2, '3': 3, '4': 4}
# Morning, noon, evening, bedtime: order of an a-b-c(-d) regimen.
SLOTS = (('아침', 'am', 'morning', 'mane'), ('점심', 'noon', 'lunch'),
         ('저녁', 'pm', 'evening'), ('취침전', '취침 전', '취침', '자기전', '자기 전', 'hs', 'qhs', 'bedtime', 'nocte', 'night'))
_SLOT_WORDS = sorted((w for group in SLOTS for w in group), key=len, reverse=True)
SLOT_RE = '(?:' + '|'.join(re.escape(w) for w in _SLOT_WORDS) + ')'
_NUM = r'\d+(?:\.\d+)?'
_TAB = r'(?:t|tab|tabs|tablet|tablets|정|알|c|cap|caps|캡슐)'


def _slot(word):
    word = word.casefold()
    return next(i for i, group in enumerate(SLOTS) if word in group)


def _abbreviations(text):
    # Dotted Latin abbreviations: b.i.d. -> bid, p.r.n. -> prn, h.s. -> hs.
    for word in ('qhs', 'qid', 'qod', 'qam', 'qpm', 'bid', 'tid', 'prn', 'qd', 'od', 'hs', 'pc', 'ac'):
        pattern = r'(?<![a-z])' + r'\.?\s?'.join(word) + r'\.?(?![a-z])'
        text = re.sub(pattern, lambda m: word if '.' in m.group() else m.group(), text, flags=re.I)
    for uk, us in (('b.d', 'bid'), ('bd', 'bid'), ('t.d.s', 'tid'), ('tds', 'tid'), ('q.d.s', 'qid'), ('qds', 'qid')):
        text = re.sub(r'(?<![a-z])' + re.escape(uk) + r'\.?(?![a-z])', us, text, flags=re.I)  # UK forms
    text = re.sub(r'(?<![a-z])q\s*(\d{1,2})\s*(?:hrs?|hours?)(?![a-z])', r'q\1h', text, flags=re.I)
    text = re.sub(r'(?<![a-z])(?:q\s?day|q24h|qn|once\s+(?:a\s+|per\s+)?day|once\s+daily)(?![a-z])', 'qd', text, flags=re.I)
    text = re.sub(r'(?<![a-z])(?:twice)\s*(?:a\s+|per\s+)?(?:day|daily)(?![a-z])', 'bid', text, flags=re.I)
    text = re.sub(r'(?<![a-z])(?:thrice|three\s+times)\s*(?:a\s+|per\s+)?(?:day|daily)(?![a-z])', 'tid', text, flags=re.I)
    text = re.sub(r'(?<![a-z])four\s+times\s*(?:a\s+|per\s+)?(?:day|daily)(?![a-z])', 'qid', text, flags=re.I)
    text = re.sub(r'(?<![a-z])every\s+other\s+day(?![a-z])|격일', 'qod', text, flags=re.I)
    # "2 times daily", "2x/day", "2x daily", "×2/day"
    text = re.sub(r'(?<![\d.])([1-4])\s*(?:x|×|times?)\s*(?:a\s+|per\s+|/\s*)?(?:day|daily|d)(?![a-z])',
                  lambda m: FREQ_WORD[int(m.group(1))], text, flags=re.I)
    text = re.sub(r'(?:x|×)\s*([1-4])\s*/\s*(?:day|d|일)(?![a-z])', lambda m: FREQ_WORD[int(m.group(1))], text, flags=re.I)
    text = re.sub(r'(?<=\d)\s*mg\s+per\s+(?:day|d)(?![a-z])', 'mg/day', text, flags=re.I)  # 'per' is also a perphenazine alias
    text = re.sub(r'(?<=\d)\s*mg\s*/\s*(?:24\s*h|일)(?![a-z])', 'mg/day', text, flags=re.I)
    return text


def _korean_frequency(text):
    # 하루 2번, 하루두번, 일 2회, 1일2회, 2회/일, 하루 한 번
    text = re.sub(r'(?:하루|1일|일)\s*(한|두|세|네|[1-4])\s*(?:번|회)', lambda m: ' ' + FREQ_WORD[KO_NUM[m.group(1)]] + ' ', text)
    text = re.sub(r'(?<![\d.])([1-4])\s*(?:번|회)\s*/\s*(?:일|day)', lambda m: ' ' + FREQ_WORD[int(m.group(1))] + ' ', text)
    text = re.sub(r'(?:하루|1일)\s*(?=\d+(?:\.\d+)?\s*mg)', '', text)  # 하루 4mg -> 4mg/day
    text = re.sub(r'1\s*日\s*([1-4])\s*回', lambda m: ' ' + FREQ_WORD[int(m.group(1))] + ' ', text)  # 1日2回
    text = re.sub(r'(?<=\d)\s*錠', 'T', text).replace('分', '#')  # 2錠 分2 = 2T#2
    # 1T씩 2회 / 1정씩 2회: n tablets each time, n times a day
    text = re.sub(r'씩\s*([1-4])\s*(?:회|번)(?!\s*/\s*(?:주|week))', lambda m: ' ' + FREQ_WORD[int(m.group(1))] + ' ', text)
    text = re.sub(r'(아침|점심|저녁)(?=점심|저녁|취침|자기)', r'\1 ', text)  # 아침저녁
    text = re.sub(r'(아침|점심|저녁)(?=점심|저녁|취침|자기)', r'\1 ', text)
    return text


def _fractions(text):
    """½T, 1/2T, 반알 -> 0.5T, only after a written strength ("2mg 1/2T"). "1/2 tablet (50 mg)" stays
    ambiguous (is 50 mg the tablet or the half?) and is held by the parser."""
    text = re.sub(r'(?<![가-힣])반\s*(?:알|정|tab|t)(?![a-z가-힣])', '½T', text, flags=re.I)
    text = re.sub(r'(?<=\d)\s*알', 'T', text)
    fraction = re.search(r'½|¼|¾|(?<![\d.])[13]\s*[/⁄]\s*[24](?![\d])', text)
    if not fraction or not re.search(r'\d\s*(?:mg|mcg|g)(?![a-z])', text[:fraction.start()], re.I):
        return text
    text = text.replace('½', '0.5').replace('¼', '0.25').replace('¾', '0.75')
    for pattern, value in ((r'1\s*[/⁄]\s*2', '0.5'), (r'1\s*[/⁄]\s*4', '0.25'), (r'3\s*[/⁄]\s*4', '0.75')):
        text = re.sub(r'(?<![\d.])' + pattern + r'(?=\s*(?:' + _TAB + r'(?![a-z])|-))|(?<=-)\s*' + pattern + r'(?![\d])',
                      value, text, flags=re.I)
    return text


def _times_multiplier(text):
    # "1T x 2", "1Tx2", "1x2" (tablets x times a day) and "2mg x2"; never "x 7days".
    not_days = r'(?!\s*(?:days?|일|wks?|weeks?|주|개월|months?))'
    text = re.sub(r'(?<![\d.])(' + _NUM + r')\s*' + _TAB + r'?\s*(?:x|×|\*)\s*([1-4])(?![\d.])' + not_days,
                  lambda m: f'{m.group(1)}T {FREQ_WORD[int(m.group(2))]}', text, flags=re.I)
    text = re.sub(r'(?<=mg)\s*(?:x|×|\*)\s*([1-4])(?![\d.])' + not_days, lambda m: ' ' + FREQ_WORD[int(m.group(1))], text, flags=re.I)
    return text


def _slot_sequences(text):
    """a-b-c written with '/', '+', dashes or tablet units, and per-slot mg doses."""
    notes = []
    text = re.sub(r'(?<=\d)\s*[–—−]\s*(?=\d)', '-', text)
    slot = r'\d(?:\.\d+)?\s*' + _TAB + r'?'
    for sep in ('/', r'\+', '-'):
        pattern = rf'(?<![\d./+-])({slot}(?:\s*{sep}\s*{slot}){{2,3}})(?![\d./+])(?!\s*mg)'
        def tablets(m, sep=sep):
            parts = re.split(r'\s*' + sep + r'\s*', m.group(1))
            return '-'.join(re.sub(r'\s*' + _TAB + r'$', '', p, flags=re.I) for p in parts)
        if sep != '-' or re.search(_TAB + r'\s*-', text, re.I):
            text = re.sub(pattern, tablets, text, flags=re.I)
    # mg in the slots: 2mg-0-2mg, 1mg-0-2mg, 100-0-200mg -> total mg/day (a-b-c without strength = mg)
    mg_slots = re.search(rf'(?<![\d.])({_NUM}(?:\s*mg)?(?:\s*-\s*{_NUM}(?:\s*mg)?){{2,3}}\s*mg)(?![a-z])', text, re.I)
    if mg_slots:
        total = sum(float(v) for v in re.findall(_NUM, mg_slots.group(1)))
        if total > 0:
            notes.append(f"시간대별 mg 합산 ({mg_slots.group(1).replace(' ', '')} → {total:g} mg/일)")
            text = text[:mg_slots.start()] + f'{total:g}mg/day' + text[mg_slots.end():]
    return text, notes


def _slot_words(text):
    """아침 1T 저녁 1T / 아침1 저녁1 (tablets) and 아침 100mg 저녁 200mg (mg) per time of day."""
    notes = []
    slot_first = list(re.finditer(rf'({SLOT_RE})\s*({_NUM})\s*(mg|{_TAB})?(?![a-z\d])', text, re.I))
    dose_first = list(re.finditer(rf'({_NUM})\s*(mg)\s*({SLOT_RE})(?![a-z가-힣])', text, re.I))
    pairs = ([(m, m.group(1), m.group(2), m.group(3)) for m in slot_first] if len(slot_first) >= 2 else
             [(m, m.group(3), m.group(1), m.group(2)) for m in dose_first])
    found = [m for m, *_ in pairs]
    if len(pairs) >= 2:
        slots, units = {}, set()
        for m, word, value, unit in pairs:
            slots[_slot(word)] = slots.get(_slot(word), 0) + float(value)
            units.add('mg' if unit and unit.casefold() == 'mg' else 'tab')
        if len(units) == 1:
            start, end = found[0].start(), found[-1].end()
            if units == {'mg'}:
                total = sum(slots.values())
                notes.append(f'시간대별 mg 합산 ({text[start:end].strip()} → {total:g} mg/일)')
                return text[:start] + f'{total:g}mg/day' + text[end:], notes
            sequence = '-'.join(f'{slots.get(i, 0):g}' for i in range(4 if 3 in slots else 3))
            return text[:start] + sequence + text[end:], notes
    # Times of day without numbers: 아침 저녁 = twice a day ("아침 저녁 1T씩" = 1 tablet at each).
    each = re.search(rf'(?<![\d.])({_NUM})\s*{_TAB}\s*씩', text, re.I)
    if each:
        text = text[:each.start()] + f'{each.group(1)}T' + text[each.end():]
    if each or not re.search(rf'{SLOT_RE}\s*\d|\d\s*(?:t|정)?\s*-\s*\d', text, re.I):
        words = {_slot(m.group()) for m in re.finditer(rf'(?<![a-z가-힣]){SLOT_RE}(?![a-z])', text, re.I)}
        if len(words) >= 2 and not re.search(r'\b(?:q?d|od|bid|tid|qid|qod)\b|\d\s*회', text, re.I):
            text = text + ' ' + FREQ_WORD.get(len(words), '')
    return text, notes


def _solution(text):
    """1mg/mL 2mL -> 2 mg per dose (concentration x volume)."""
    m = re.search(rf'({_NUM})\s*mg\s*/\s*({_NUM})?\s*(?:ml|cc)\b(.*?)(?<![\d.])({_NUM})\s*(?:ml|cc)\b', text, re.I)
    if not m:
        return text, []
    per_ml = float(m.group(1)) / float(m.group(2) or 1)
    dose = per_ml * float(m.group(4))
    note = f'농도 × 부피 ({m.group(1)} mg/{m.group(2) or 1} mL × {m.group(4)} mL = {dose:g} mg/회)'
    rest = re.sub(r'\b(?:oral\s+solution|solution|liquid|syrup|drops?|내용액|시럽|액)\b', '', m.group(3), flags=re.I)
    return text[:m.start()] + f'{dose:g}mg' + rest + text[m.end():], [note]


def normalize_notation(text):
    original = text
    text = re.sub(r'(?<=[a-z가-힣]{3})-(?=\d)', ' ', text, flags=re.I)  # risperidone-2mg
    text = re.sub(r'(?<=\d),(?=\d\s*mg)', '.', text, flags=re.I)  # 2,5mg (thousands are removed earlier)
    text = _abbreviations(text)
    text = _korean_frequency(text)
    text = _fractions(text)
    text, solution_notes = _solution(text)
    text = _times_multiplier(text)
    text, slot_notes = _slot_sequences(text)
    text, word_notes = _slot_words(text)
    text = re.sub(r'\s+', ' ', text).strip() if text != original else text
    return text, solution_notes + slot_notes + word_notes
