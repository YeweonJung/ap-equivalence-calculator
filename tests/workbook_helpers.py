"""Read the user-facing compact workbook without changing its content."""
from services.result_summary import TARGETS

def records(wb, name):
    values = list(wb[name].values)
    if name != 'Results':
        return [dict(zip(values[0], row)) for row in values[1:]]
    headers = list(values[6])
    labels = {'환자 ID': 'patient_id', '환산 상태': '결과 상태', '확인할 사항': '확인할 내용'}
    labels.update({m.replace('CMD_', 'CMD\n') + '\n' + t + ' mg/day': f'{m} ({t} mg/day)' for m,t in TARGETS.items()})
    headers = [labels.get(h, h) for h in headers]
    return [dict(zip(headers, [None if v == '—' else v for v in row])) for row in values[7:]]
