"""Preserve bracket annotations and original character offsets."""
SEPARATORS = {';', ',', '\n', '+'}


def split_medication_spans(text):
    text = '' if text is None else str(text)
    stack, start, spans = [], 0, []
    pairs = {')': '(', ']': '[', '}': '{', '）': '（'}
    for index, char in enumerate(text):
        if char in pairs.values():
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                raise ValueError('괄호 짝이 맞지 않습니다. 원문을 확인해 주세요.')
        elif char in SEPARATORS and not stack:
            if text[start:index].strip():
                left = start + len(text[start:index]) - len(text[start:index].lstrip())
                spans.append((left, left + len(text[start:index].strip()), text[start:index].strip()))
            start = index + 1
    if stack:
        raise ValueError('괄호 짝이 맞지 않습니다. 원문을 확인해 주세요.')
    if text[start:].strip():
        left = start + len(text[start:]) - len(text[start:].lstrip())
        spans.append((left, left + len(text[start:].strip()), text[start:].strip()))
    return spans


def split_medications(text):
    return [value for _, _, value in split_medication_spans(text)]
