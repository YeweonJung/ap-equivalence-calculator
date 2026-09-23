"""Explain unavailable patient totals without changing any calculated values."""
from collections import defaultdict

NOTE_COLUMNS = ['결과 상태', '확인할 내용']


def with_result_notes(patient_rows, audit_rows, error_rows, patient_checks):
    audits, errors, checks = (defaultdict(list) for _ in range(3))
    for row in audit_rows:
        audits[str(row.get('patient', ''))].append(row)
    for row in error_rows:
        errors[str(row.get('patient', ''))].append(row)
    for row in patient_checks:
        checks[str(row.get('patient_id', ''))].append(row)
    result = []
    for row in patient_rows:
        patient = str(row['patient_id'])
        notes = []
        for issue in errors[patient]:
            reason = issue.get('error') or issue.get('status_message')
            if reason:
                original = issue.get('original') or ''
                notes.append(f'{original}: {reason}' if original else str(reason))
        for item in audits[patient]:
            if item.get('warning'):
                notes.append(f"{item.get('original') or ''}: {item['warning']}")
        unavailable = [c['method'] for c in checks[patient]
                       if c.get('status') == 'incomplete']
        complete = [c for c in checks[patient] if c.get('status') == 'complete']
        if not audits[patient]:
            notes.append('약물 입력이 없습니다. 원본 처방을 확인하세요.')
        elif unavailable and not errors[patient]:
            notes.append('환산 계수 또는 제형별 근거 없음: ' + ', '.join(unavailable))
        if unavailable:
            notes.append('빈칸은 0이 아닙니다. 미환산 약물이 있는 방법은 총합계를 표시하지 않습니다.')
        if errors[patient] or any(a.get('needs_review') for a in audits[patient]):
            status = '입력 확인 필요'
        elif complete and unavailable:
            status = '일부 방법 환산 불가'
        elif complete:
            status = '환산 완료'
        elif not audits[patient]:
            status = '약물 입력 없음'
        elif all(a.get('status') == 'non_target' for a in audits[patient]):
            status = '환산 대상 없음'
            notes.append('입력된 약물은 환산 대상이 아닙니다.')
        else:
            status = '환산 불가'
        result.append({**row, '결과 상태': status,
                       '확인할 내용': '\n'.join(dict.fromkeys(notes))})
    return result
