"""One medication per row; original-cell totals appear only once."""
METHOD_ORDER = ('CMD', 'MED', 'ED95', 'DDD', 'CPZ_FGA', 'WOODS', 'GARDNER', 'CMD_DIRECT', 'CMD_INDIRECT')
TARGETS = {'CMD_DIRECT': 'OLZ', 'CMD_INDIRECT': 'OLZ', 'CMD': 'CPZ', 'MED': 'OLZ', 'ED95': 'OLZ', 'DDD': 'CPZ', 'CPZ_FGA': 'CPZ', 'WOODS': 'CPZ', 'GARDNER': 'CPZ'}


def value_column(method, total=False):
    return f'{method} {"총 환산값" if total else "약물별 환산값"} ({TARGETS[method]} mg/day)'


RESULT_COLUMNS = ['patient', 'original', '약물'] + [value_column(m) for m in METHOD_ORDER] + [value_column(m, True) for m in METHOD_ORDER] + ["환산 근거"]


def result_rows(original, patient, items, totals):
    rows = []
    for index, item in enumerate(items):
        row = dict(patient=patient, original=original, 약물=item.get('drug') or item['original'])
        row['환산 근거'] = item.get('warning', '') if item.get('route') == 'injection' else ''
        for conversion in item['conversions']:
            row[value_column(conversion['method'])] = conversion['value']
        if index == 0:
            for total in totals:
                row[value_column(total['method'], True)] = total['total_equivalent_dose_mg']
        rows.append(row)
    return rows


PATIENT_METHOD_ORDER = ('CMD', 'MED', 'DDD', 'ED95', 'GARDNER', 'WOODS', 'CPZ_FGA', 'CMD_DIRECT', 'CMD_INDIRECT')
PATIENT_COLUMNS = ['patient_id'] + [f'{m} ({TARGETS[m]} mg/day)' for m in PATIENT_METHOD_ORDER]


def patient_results(patients, methods):
    """Aggregate all source rows for an ID, rounding only after summation."""
    from services.frames import summarize_frames
    rows, checks = [], []
    for patient, items in patients.items():
        row = {'patient_id': patient}
        for total in summarize_frames(items, methods):
            row[f"{total['method']} ({TARGETS[total['method']]} mg/day)"] = total['total_equivalent_dose_mg']
            checks.append({'patient_id': patient, **total})
        rows.append(row)
    return rows, checks
