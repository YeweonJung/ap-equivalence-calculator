import zipfile

import pytest

from services.longitudinal import analyze, analyze_export, export_zip, reference_pairs
from tests.test_longitudinal import prepared, rx


@pytest.mark.parametrize('rows', [[], [rx()], [
    rx(patient='=formula'), rx(patient='=formula'),
    rx('2020-04-26', tabs='1', patient='=formula'),
    rx(patient='0001', drug='unknown 2mg tab'),
    rx(patient='0002', drug='lorazepam 1mg tab'),
]])
def test_spooled_export_matches_in_memory_results_byte_for_byte(rows):
    records = prepared(rows) if rows else []
    pairs = reference_pairs(records, 'all_dates') if records else []
    results, details = analyze(records, pairs)
    old = zipfile.ZipFile(export_zip(records, results, details, {}))
    new = zipfile.ZipFile(analyze_export(records, pairs, {}))
    assert old.namelist() == new.namelist()
    for name in old.namelist():
        assert old.read(name) == new.read(name), name


def test_streamed_details_are_not_retained_and_output_limit_still_applies():
    records = prepared([rx()])
    pairs = reference_pairs(records, 'all_dates')
    emitted = []
    results, details = analyze(records, pairs, ['DDD'], detail_sink=emitted.append)
    assert len(results) == len(emitted) == 1 and details == []
    class OversizedMethods(list):
        def __len__(self):
            return 400001
    with pytest.raises(ValueError, match='400,000'):
        analyze(records, pairs, OversizedMethods(['DDD']), detail_sink=lambda row: None)
