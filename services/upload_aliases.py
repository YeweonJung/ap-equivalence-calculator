"""Exact upload aliases explicitly confirmed by the user on 2026-09-23.

These are not fuzzy matches or generated candidates. Keep the original input
and record the mapping in the audit trail. `zir` requires reviewer attention.
"""
CONFIRMED_UPLOAD_ALIASES = {
    'clop': ('clopenthixol', False),
    'rispl': ('risperidone', False),
    'olx': ('olanzapine', False),
    'abil': ('aripiprazole', False),
    'zir': ('ziprasidone', True),
    'pariperidone': ('paliperidone', False),
    'aripiprazold': ('aripiprazole', False),
    'queiapine': ('quetiapine', False),
}


def parse_upload_frames(text):
    """Apply confirmed leading names per frame, retaining source character spans."""
    import re
    from services.frames import parse_frames
    frames = parse_frames(text)
    for index, frame in enumerate(frames):
        if frame['status'] != 'unknown_drug':
            continue
        original = frame['original']
        match = re.match(r'([A-Za-z]+)(?=\s|\d|\(|\[|$)', original)
        approved = CONFIRMED_UPLOAD_ALIASES.get(match[1].casefold()) if match else None
        if not approved:
            continue
        corrected = approved[0] + original[match.end():]
        if frame['route'] == 'injection':
            corrected += ' LAI'
        parsed = parse_frames(corrected)
        if len(parsed) != 1:
            continue
        replacement = parsed[0]
        replacement.update(original=original, source_start=frame['source_start'],
                           source_end=frame['source_end'], match_type='user_confirmed_alias')
        note = f'사용자 확인 약어/표기: {match[1]} → {approved[0]}'
        if approved[1]:
            replacement['needs_review'] = True
            note += ' (REVIEW_REQUIRED)'
        replacement['warning'] = '; '.join(filter(None, [replacement.get('warning'), note]))
        frames[index] = replacement
    return frames
