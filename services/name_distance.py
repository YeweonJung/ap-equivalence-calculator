"""Deterministic character alignment (optimal string alignment distance).

Insertion, deletion, substitution and adjacent transposition cost one each.
Scores describe spelling similarity, never clinical confidence.
"""
def compare_letters(source, target):
    rows, cols = len(source) + 1, len(target) + 1
    cost = [[0] * cols for _ in range(rows)]
    step = {}
    for i in range(1, rows):
        cost[i][0] = i
        step[i, 0] = (i-1, 0, 'delete')
    for j in range(1, cols):
        cost[0][j] = j
        step[0, j] = (0, j-1, 'insert')
    for i in range(1, rows):
        for j in range(1, cols):
            equal = source[i-1] == target[j-1]
            choices = [(cost[i-1][j-1] + (not equal), i-1, j-1, 'equal' if equal else 'replace'),
                       (cost[i-1][j]+1, i-1, j, 'delete'),
                       (cost[i][j-1]+1, i, j-1, 'insert')]
            if i > 1 and j > 1 and source[i-2:i] == target[j-2:j][::-1]:
                choices.insert(0, (cost[i-2][j-2]+1, i-2, j-2, 'transpose'))
            value, a, b, operation = min(choices, key=lambda x: x[0])
            cost[i][j], step[i, j] = value, (a, b, operation)
    edits, i, j = [], len(source), len(target)
    while i or j:
        a, b, operation = step[i, j]
        if operation != 'equal':
            edits.append(dict(operation=operation, position=a+1, source=source[a:i], target=target[b:j]))
        i, j = a, b
    distance = cost[-1][-1]
    return dict(distance=distance, score=round(100*(1-distance/max(len(source), len(target), 1)), 1),
                edits=list(reversed(edits)))


BRANDS = set("solian abilify maintena saphris rexulti largactil clozaril prolixin haldol fanapt latuda zyprexa zypadhera byannli invega trevicta xeplion perphenan seroquel okedi risperdal serdolect mellaril navane stelazine geodon lodopin sustenna trinza hafyera aristada asimtufii".split())
