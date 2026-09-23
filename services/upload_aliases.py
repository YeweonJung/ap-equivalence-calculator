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
}
