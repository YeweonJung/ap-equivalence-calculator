"""Pair parallel drug/dose cells without guessing missing values."""
import re
from services.frames import parse_frames
from services.medication_splitter import split_medications
from services.parser import DOSE_RE, _frequency_matches, alias_map
from services.upload_aliases import CONFIRMED_UPLOAD_ALIASES


def _parallel_doses(text):
    result = []
    token = r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:\s*(?:mcg|ug|μg|㎍|mg|㎎|g))?'
    for part in split_medications(text):
        if re.fullmatch(rf'{token}(?:\s+{token})+', part, re.I):
            result.extend(m.group().strip() for m in re.finditer(token, part, re.I))
        else:
            result.append(part)
    return result


def _parallel_names(parts, count):
    """Keep registered multiword names intact; unknown tokens stay unconfirmed."""
    if len(parts) >= count:
        return parts
    result = []
    for part in parts:
        words = part.split()
        index = 0
        while index < len(words):
            end = next((end for end in range(len(words), index, -1)
                        if ' '.join(words[index:end]).casefold() in alias_map), index + 1)
            result.append(' '.join(words[index:end]))
            index = end
    # Only a complete, positional pairing is allowed. No dose is broadcast.
    return result if len(result) == count else parts


def _parallel_codes(text, pattern):
    result = []
    for part in split_medications(text):
        words = part.split()
        result.extend(words if len(words) > 1 and all(re.fullmatch(pattern, w, re.I) for w in words) else [part])
    return result or ['']


def structured_frames(row, raw, dose_col, unit_col, frequency_col, compose):
    def value(column):
        result = str(row.get(column, '')).strip() if column is not None else ''
        return '' if result.casefold() in {'nan', 'none', 'null'} else result

    if DOSE_RE.search(raw) or dose_col is None:
        return parse_frames(raw)
    try:
        drugs = split_medications(raw)
        doses = _parallel_doses(value(dose_col))
        drugs = _parallel_names(drugs, len(doses))
        units = _parallel_codes(value(unit_col), r'mcg|ug|μg|㎍|mg|㎎|g')
        frequencies = _parallel_codes(value(frequency_col), r'QD|BID|TID|QID|QHS|HS|QAM|QOD|[1-4](?:\.0)?|0\.5')
    except ValueError:
        return parse_frames(raw)
    frames = []
    if len(doses) != len(drugs) or len(units) not in {1, len(drugs)} or len(frequencies) not in {1, len(drugs)}:
        frames = parse_frames(raw)
        for frame in frames:
            frame.update(status='review', status_message='약물·용량 개수 불일치', warning='약물과 용량은 같은 순서와 개수로 입력해 주세요.', needs_review=True)
        return frames
    for index, drug in enumerate(drugs):
        local = row.copy()
        local[dose_col] = doses[index]
        # Synthetic column names also preserve supplied values when headers are absent.
        local_unit = unit_col or '__unit'
        local_frequency = frequency_col or '__frequency'
        local[local_unit] = units[index if len(units) > 1 else 0]
        embedded = DOSE_RE.fullmatch(doses[index])
        unit_conflict = False
        if embedded:
            supplied = local[local_unit]
            canonical = {'㎎': 'mg', '㎍': 'mcg', 'ug': 'mcg', 'μg': 'mcg'}
            normalize = lambda u: canonical.get(u.casefold(), u.casefold())
            unit_conflict = bool(supplied and normalize(supplied) != normalize(embedded['unit']))
            local[dose_col] = embedded['dose']
            local[local_unit] = embedded['unit']
        frequency = frequencies[index if len(frequencies) > 1 else 0]
        local[local_frequency] = frequency
        original_text = compose(local, drug, dose_col, local_unit, local_frequency)
        approved_alias = CONFIRMED_UPLOAD_ALIASES.get(drug.casefold())
        text = compose(local, approved_alias[0] if approved_alias else drug,
                       dose_col, local_unit, local_frequency)
        parsed = parse_frames(text)
        daily = any(word in str(dose_col).casefold() for word in ('daily', '일일', '1일'))
        valid_frequency = not frequency or daily
        if not valid_frequency:
            try:
                valid_frequency = bool(_frequency_matches(frequency)) or bool(re.fullmatch(r'(?:[1-9]|1\d|2[0-4])(?:\.0)?|0\.5', frequency))
            except ValueError:
                valid_frequency = False
        for frame in parsed:
            if approved_alias:
                frame.update(original=original_text, source_start=0, source_end=len(original_text),
                             match_type='user_confirmed_alias')
                note = f'사용자 확인 약어: {drug} → {approved_alias[0]}'
                if approved_alias[1]:
                    note += ' (REVIEW_REQUIRED)'
                    frame['needs_review'] = True
                frame['warning'] = '; '.join(filter(None, [frame.get('warning'), note]))
            if unit_conflict:
                frame.update(status='review', status_message='용량 단위 불일치',
                             warning='용량 셀과 단위 열의 단위가 다릅니다. 원본을 확인하세요.',
                             daily_dose_mg=None, needs_review=True)
            lai_frequency = frame.get('route') == 'injection' and bool(re.fullmatch(
                r'q\s*\d+\s*(?:d|days?|w|wk|weeks?|mo|months?)|every\s+\d+\s+(?:days?|weeks?|months?)|monthly|weekly|매월|매주|\d+\s*개월|\d+\s*주\s*(?:마다|간격)', frequency, re.I))
            if not valid_frequency and not lai_frequency:
                frame.update(status='review', status_message='복용 빈도 확인 필요', warning=f'지원하지 않는 복용 빈도: {frequency}. BID 등 명확한 표기를 사용해 주세요.', daily_dose_mg=None, needs_review=True)
        frames.extend(parsed)
    return frames
