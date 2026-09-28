"""One medication per row; patient totals belong only on the summary."""
METHOD_ORDER = ('CMD', 'MED', 'ED95', 'DDD', 'CPZ_FGA', 'WOODS', 'GARDNER', 'CMD_DIRECT', 'CMD_INDIRECT')
TARGETS = {'CMD_DIRECT': 'OLZ', 'CMD_INDIRECT': 'OLZ', 'CMD': 'CPZ', 'MED': 'OLZ', 'ED95': 'OLZ', 'DDD': 'CPZ', 'CPZ_FGA': 'CPZ', 'WOODS': 'CPZ', 'GARDNER': 'CPZ'}


def value_column(method, total=False):
    return f'{method} {"총 환산값" if total else "약물별 환산값"} ({TARGETS[method]} mg/day)'


def result_rows(original, patient, items):
    rows = []
    for item in items:
        row = dict(patient=patient, original=original, 약물=item.get('drug') or item['original'])
        notes = list(filter(None, [item.get('error'), item.get('warning')]))
        missing = [c['method'] for c in item['conversions'] if c['value'] is None]
        if missing:
            notes.append('환산 계수 또는 제형별 근거 없음: ' + ', '.join(missing))
        if item.get('status') == 'non_target':
            notes.append('항정신병약 환산 대상 아님')
        row['환산 근거'] = '; '.join(dict.fromkeys(notes))
        for conversion in item['conversions']:
            row[value_column(conversion['method'])] = conversion['value']
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
