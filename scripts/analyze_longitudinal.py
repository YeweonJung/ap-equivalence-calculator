"""Local-only batch analysis. Clinical input/output must stay outside Git."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.datastructures import FileStorage
from services.longitudinal_api import read_csv_upload
from services.longitudinal import analyze, detect_mapping, export_zip, prepare, reference_pairs
from services.release import metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--policy', choices=['review', 'replace'], default='review')
    parser.add_argument('--date')
    parser.add_argument('--references', type=Path)
    parser.add_argument('--all-dates', action='store_true')
    parser.add_argument('--confirm-daily-tablets', action='store_true', required=True)
    args = parser.parse_args()
    if sum([bool(args.date), bool(args.references), args.all_dates]) != 1:
        parser.error('Choose exactly one of --date, --references, --all-dates')
    repo = Path(__file__).resolve().parents[1]
    if args.output.resolve().is_relative_to(repo):
        parser.error('Output must be outside the source repository')
    started = perf_counter()
    with args.input.open('rb') as source:
        frame, digest = read_csv_upload(FileStorage(source, filename=args.input.name))
    mapping = detect_mapping(frame.columns)
    records = prepare(frame, mapping, args.policy)
    refs = None
    if args.references:
        with args.references.open('rb') as source:
            refs, _ = read_csv_upload(FileStorage(source, filename=args.references.name))
    mode = 'all_dates' if args.all_dates else 'per_patient' if args.references else 'common'
    pairs = reference_pairs(records, mode, args.date or '', refs)
    results, details = analyze(records, pairs, policy=args.policy)
    metadata_dict = dict(policy=args.policy, mode=mode, mapping=mapping, source_sha256=digest, date_basis='prescription_date_as_start', dose_basis='tablets_per_day', release=metadata())
    out = export_zip(records, results, details, metadata_dict)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as destination:
        destination.write(out.getbuffer())
    summary = dict(rows=len(records), patients=len({r['patient'] for r in records if r['patient']}), reference_pairs=len(pairs), policy=args.policy, result_statuses=dict(Counter(r['status'] for r in results)), row_issues=dict(Counter(i for r in records for i in set(r['issues']))), adjusted_rows=sum(bool(r['adjustments']) for r in records), seconds=round(perf_counter()-started, 2), source_sha256=digest)
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == '__main__':
    main()
