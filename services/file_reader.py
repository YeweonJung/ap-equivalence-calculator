import csv
import io
import pandas as pd
from zipfile import BadZipFile

from services.column_detector import MEDICATION_KEYWORDS

MAX_SHEETS = 5


def validate_headers(columns):
    # Validate before pandas silently renames duplicate headers with .1 suffixes.
    named = [str(c).strip().casefold() for c in columns if str(c).strip()]
    if len(named) != len(set(named)):
        raise ValueError('중복 열 이름을 구분한 뒤 다시 업로드하세요.')


def csv_layout(text):
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip()), None)
    if start is None:
        raise ValueError('CSV 파일에 열 이름이나 데이터가 없습니다.')
    try:
        separator = csv.Sniffer().sniff(lines[start], delimiters=',;\t|').delimiter
    except csv.Error:
        separator = ','
    try:
        columns = next(csv.reader(io.StringIO(''.join(lines[start:])), delimiter=separator))
    except (csv.Error, StopIteration) as exc:
        raise ValueError('CSV 열 이름을 읽을 수 없습니다.') from exc
    validate_headers(columns)
    return separator, start


def _header_score(frame):
    if not len(frame.columns):
        return -1
    columns = [str(column).casefold().strip() for column in frame.columns]
    named = sum(not column.startswith("unnamed:") for column in columns) / len(columns)
    keyword = sum(any(word in column for word in MEDICATION_KEYWORDS) for column in columns)
    return named + keyword * 3


def _read_excel_sheet(filepath, sheet):
    candidates = []
    for header in range(5):
        try:
            frame = pd.read_excel(filepath, sheet_name=sheet, header=header, nrows=5, dtype=str, keep_default_na=False)
            candidates.append((_header_score(frame), -header, frame))
        except (ValueError, IndexError):
            continue
    if not candidates:
        raise ValueError(f"'{sheet}' 시트를 읽을 수 없습니다.")
    _, negative_header, _ = max(candidates, key=lambda item: (item[0], item[1]))
    raw_header = pd.read_excel(filepath, sheet_name=sheet, header=None,
                               skiprows=-negative_header, nrows=1, dtype=str, keep_default_na=False)
    if not raw_header.empty:
        validate_headers(raw_header.iloc[0].tolist())
    frame = pd.read_excel(filepath, sheet_name=sheet, header=-negative_header,
                          dtype=str, keep_default_na=False)
    frame.attrs["header_row"] = -negative_header
    return frame


def read_file(filepath):

    if filepath.lower().endswith(
        ".csv"
    ):

        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
            try:
                with open(filepath, encoding=encoding, newline='') as source:
                    separator, header_row = csv_layout(source.read())
                frame = pd.read_csv(filepath, encoding=encoding, sep=separator, engine="c", dtype=str, keep_default_na=False, skip_blank_lines=False, skiprows=header_row).fillna('')
                frame.attrs["header_row"] = header_row
                return {"Sheet1": frame}
            except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
                last_error = exc
        raise ValueError("CSV 인코딩 또는 구분자를 확인할 수 없습니다.") from last_error

    try:
        excel = pd.ExcelFile(filepath)
    except (ValueError, OSError, BadZipFile) as exc:
        raise ValueError("Excel 파일이 손상되었거나 실제 Excel 형식이 아닙니다.") from exc
    with excel:
        if len(excel.sheet_names) > MAX_SHEETS:
            raise ValueError(f"Excel 시트는 최대 {MAX_SHEETS}개까지 처리할 수 있습니다.")
        return {sheet: _read_excel_sheet(excel, sheet) for sheet in excel.sheet_names}

