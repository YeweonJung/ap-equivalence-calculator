"""One medication per row; original-cell totals appear only once."""
METHOD_ORDER = ('CMD', 'MED', 'ED95', 'DDD', 'CPZ_FGA')
TARGETS = {'CMD': 'CPZ', 'MED': 'OLZ', 'ED95': 'OLZ', 'DDD': 'CPZ', 'CPZ_FGA': 'CPZ'}


def value_column(method, total=False):
    return f'{method} {"총 환산값" if total else "약물별 환산값"} ({TARGETS[method]} mg/day)'


RESULT_COLUMNS = ['patient', 'original', '약물'] + [value_column(m) for m in METHOD_ORDER] + [value_column(m, True) for m in METHOD_ORDER]


def result_rows(original, patient, items, totals):
    rows = []
    for index, item in enumerate(items):
        row = dict(patient=patient, original=original, 약물=item.get('drug') or item['original'])
        for conversion in item['conversions']:
            row[value_column(conversion['method'])] = conversion['value']
        if index == 0:
            for total in totals:
                row[value_column(total['method'], True)] = total['total_equivalent_dose_mg']
        rows.append(row)
    return rows
