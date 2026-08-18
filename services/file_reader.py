import pandas as pd
from zipfile import BadZipFile

from services.column_detector import MEDICATION_KEYWORDS

MAX_SHEETS = 5


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
            frame = pd.read_excel(filepath, sheet_name=sheet, header=header)
            candidates.append((_header_score(frame), -header, frame))
        except (ValueError, IndexError):
            continue
    if not candidates:
        raise ValueError(f"'{sheet}' 시트를 읽을 수 없습니다.")
    _, negative_header, frame = max(candidates, key=lambda item: (item[0], item[1]))
    frame.attrs["header_row"] = -negative_header
    return frame


def read_file(filepath):

    if filepath.lower().endswith(
        ".csv"
    ):

        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
            try:
                frame = pd.read_csv(filepath, encoding=encoding, sep=None, engine="python")
                frame.attrs["header_row"] = 0
                return {"Sheet1": frame}
            except (UnicodeDecodeError, pd.errors.ParserError) as exc:
                last_error = exc
        raise ValueError("CSV 인코딩 또는 구분자를 확인할 수 없습니다.") from last_error

    try:
        with pd.ExcelFile(filepath) as excel:
            sheet_names = list(excel.sheet_names)
    except (ValueError, OSError, BadZipFile) as exc:
        raise ValueError("Excel 파일이 손상되었거나 실제 Excel 형식이 아닙니다.") from exc

    if len(sheet_names) > MAX_SHEETS:
        raise ValueError(f"Excel 시트는 최대 {MAX_SHEETS}개까지 처리할 수 있습니다.")

    sheets = {}

    for sheet in sheet_names:
        sheets[sheet] = _read_excel_sheet(filepath, sheet)

    return sheets
