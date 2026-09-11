"""Pair parallel drug/dose cells without guessing missing values."""
import re
from services.frames import parse_frames
from services.medication_splitter import split_medications
from services.parser import DOSE_RE, _frequency_matches


def structured_frames(row, raw, dose_col, unit_col, frequency_col, compose):
    def value(column):
        result = str(row.get(column, '')).strip() if column is not None else ''
        return '' if result.casefold() in {'nan', 'none', 'null'} else result

    if DOSE_RE.search(raw) or dose_col is None:
        return parse_frames(raw)
    try:
        drugs = split_medications(raw)
        doses = split_medications(value(dose_col))
        units = split_medications(value(unit_col)) or ['']
        frequencies = split_medications(value(frequency_col)) or ['']
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
        frequency = frequencies[index if len(frequencies) > 1 else 0]
        local[local_frequency] = frequency
        text = compose(local, drug, dose_col, local_unit, local_frequency)
        parsed = parse_frames(text)
        daily = any(word in str(dose_col).casefold() for word in ('daily', '일일', '1일'))
        valid_frequency = not frequency or daily
        if not valid_frequency:
            try:
                valid_frequency = bool(_frequency_matches(frequency)) or bool(re.fullmatch(r'(?:[1-9]|1\d|2[0-4])(?:\.0)?|0\.5', frequency))
            except ValueError:
                valid_frequency = False
        for frame in parsed:
            if not valid_frequency:
                frame.update(status='review', status_message='복용 빈도 확인 필요', warning=f'지원하지 않는 복용 빈도: {frequency}. BID 등 명확한 표기를 사용해 주세요.', daily_dose_mg=None, needs_review=True)
        frames.extend(parsed)
    return frames
