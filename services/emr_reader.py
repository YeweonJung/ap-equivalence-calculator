"""Read a prescription table exported from any hospital record system for the hospital data page.

Hospital exports vary: real .xlsx/.xls files, '.xls' files that are really web pages or text,
UTF-16 text, title rows above the table, repeated header rows, duplicate or blank column names,
and help sheets next to the data. Everything is read as text; nothing is guessed about meaning
(the researcher links each column by hand). Original row numbers are kept for the audit trail.
"""
import csv
import datetime
import io
import re
import unicodedata

HEADER_SCAN = 15          # rows searched for the header row
OLE2 = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
ENCRYPTED = 'E\x00n\x00c\x00r\x00y\x00p\x00t\x00i\x00o\x00n\x00I\x00n\x00f\x00o'.encode('latin-1')


class TableError(ValueError):
    pass


def _cell(value):
    if value is None:
        return ''
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S') if (value.hour, value.minute, value.second) != (0, 0, 0) else value.strftime('%Y-%m-%d')
    if isinstance(value, datetime.date):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() and abs(value) < 1e15 else repr(value)
    if isinstance(value, bool):
        return str(value).upper()
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', str(value)).replace('﻿', '').replace('​', '')).strip()


def _xlsx_grids(raw, limit):
    from openpyxl import load_workbook
    try:
        book = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:
        raise TableError('Excel 파일을 열 수 없습니다. Excel에서 열어 "다른 이름으로 저장 → Excel 통합 문서(.xlsx)"로 저장한 뒤 올려 주세요.') from exc
    try:
        for sheet in book.worksheets:
            rows = []
            for number, values in enumerate(sheet.iter_rows(values_only=True), start=1):
                cells = [_cell(v) for v in values]
                if any(cells):
                    rows.append((number, cells))
                    if len(rows) > limit:
                        break
            yield sheet.title, rows
    finally:
        book.close()


def _xls_grids(raw, limit):
    if ENCRYPTED in raw[:200000] or b'EncryptedPackage' in raw[:200000].replace(b'\x00', b''):
        raise TableError('암호가 걸린 파일입니다. Excel에서 암호를 해제하고 저장한 뒤 올려 주세요.')
    import xlrd
    try:
        book = xlrd.open_workbook(file_contents=raw, on_demand=True)
    except Exception as exc:
        raise TableError('Excel 파일을 열 수 없습니다. Excel에서 열어 "다른 이름으로 저장 → Excel 통합 문서(.xlsx)"로 저장한 뒤 올려 주세요.') from exc
    try:
        for index in range(book.nsheets):
            sheet = book.sheet_by_index(index)
            rows = []
            for r in range(sheet.nrows):
                cells = []
                for c in range(sheet.ncols):
                    cell = sheet.cell(r, c)
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        try:
                            cells.append(_cell(xlrd.xldate.xldate_as_datetime(cell.value, book.datemode)))
                            continue
                        except Exception:
                            pass
                    cells.append(_cell(cell.value))
                if any(cells):
                    rows.append((r + 1, cells))
                    if len(rows) > limit:
                        break
            yield sheet.name, rows
            book.unload_sheet(index)
    finally:
        book.release_resources()


def _decode(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return raw.decode('utf-16')
    if raw.startswith(b'\xef\xbb\xbf'):
        return raw[3:].decode('utf-8', errors='replace')
    head = raw[:4000]
    if head and head.count(b'\x00') > len(head) // 4:   # UTF-16 without a byte-order mark
        return raw.decode('utf-16-le' if head[1:2] == b'\x00' else 'utf-16-be', errors='replace')
    for encoding in ('utf-8', 'cp949'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(raw[:200000]).best()
        if best is not None:
            return raw.decode(best.encoding, errors='replace')
    except Exception:
        pass
    raise TableError('파일 글자 인코딩을 알 수 없습니다. Excel에서 열어 "CSV UTF-8" 또는 Excel 통합 문서(.xlsx)로 저장한 뒤 올려 주세요.')


def _html_grids(text, limit):
    import lxml.html
    try:
        root = lxml.html.fromstring(text)
    except Exception as exc:
        raise TableError('파일 안의 표를 읽을 수 없습니다. Excel에서 열어 Excel 통합 문서(.xlsx)로 저장한 뒤 올려 주세요.') from exc
    for number, table in enumerate(root.iter('table'), start=1):
        rows = []
        for line, tr in enumerate(table.iter('tr'), start=1):
            if tr.getparent() is not None and any(a.tag == 'table' for a in tr.iterancestors() if a is not table):
                continue   # rows of a nested table are read with that table
            cells = []
            for td in tr:
                if td.tag not in ('td', 'th'):
                    continue
                text = _cell(td.text_content())
                # Excel web-page exports show '#####' in narrow date columns; the value is kept in x:num.
                if re.fullmatch(r'#+', text) and td.get('x:num'):
                    text = _cell(td.get('x:num'))
                cells.append(text)
                try:
                    span = min(int(td.get('colspan', 1)), 50)
                except ValueError:
                    span = 1
                cells.extend([''] * (span - 1))
            if any(cells):
                rows.append((line, cells))
                if len(rows) > limit:
                    break
        yield f'표{number}', rows


def _text_grid(text, limit):
    lines = text.splitlines()
    sample = [line for line in lines[:60] if line.strip()]
    best, best_score = ',', -1
    for delimiter in ('\t', ',', ';', '|'):
        counts = [len(next(csv.reader([line], delimiter=delimiter))) for line in sample[:40]]
        wide = [n for n in counts if n > 1]
        if not wide:
            continue
        common = max(set(wide), key=wide.count)
        score = wide.count(common) * common
        if score > best_score:
            best, best_score = delimiter, score
    rows = []
    reader = csv.reader(io.StringIO(text), delimiter=best)
    try:
        for number, values in enumerate(reader, start=1):
            cells = [_cell(v) for v in values]
            if any(cells):
                rows.append((number, cells))
                if len(rows) > limit:
                    break
    except csv.Error as exc:
        raise TableError(f'{len(rows) + 1}번째 줄 근처를 읽을 수 없습니다. Excel에서 열어 Excel 통합 문서(.xlsx)로 저장한 뒤 올려 주세요.') from exc
    yield '', rows


def _grids(raw, limit):
    if not raw.strip():
        raise TableError('빈 파일입니다. 처방 자료가 들어 있는 파일을 올려 주세요.')
    if raw.startswith(b'PK\x03\x04'):
        return list(_xlsx_grids(raw, limit))
    if raw.startswith(OLE2):
        return list(_xls_grids(raw, limit))
    if raw.lstrip()[:5] == b'%PDF-':
        raise TableError('PDF 파일은 읽을 수 없습니다. 전산실에 Excel이나 CSV 파일로 받아 주세요.')
    text = _decode(raw)
    if re.search(r'<\s*table\b', text[:500000], re.I):
        return list(_html_grids(text, limit))
    return list(_text_grid(text, limit))


def _norm(value):
    return re.sub(r'[\s_\-().\[\]/]', '', unicodedata.normalize('NFKC', str(value))).casefold()


def _texty(cell):
    value = cell.strip()
    if not value:
        return False
    if re.fullmatch(r'[-+]?[\d.,/:\s]+', value):
        return False
    return not re.fullmatch(r'\d{4}[-./년]\s*\d{1,2}.*', value)


def _header_index(rows, aliases):
    best, best_score = 0, None
    for i, (_, cells) in enumerate(rows[:HEADER_SCAN]):
        filled = [c for c in cells if c.strip()]
        if len(filled) < 2:
            continue
        hits = sum(_norm(c) in aliases for c in filled)
        score = hits * 10 + sum(_texty(c) for c in filled) - (len(filled) - sum(_texty(c) for c in filled)) * 2
        if best_score is None or score > best_score:
            best, best_score = i, score
    return best


def _frame(rows, aliases):
    import pandas as pd
    h = _header_index(rows, aliases)
    header_number, header = rows[h]
    body = rows[h + 1:]
    width = max([len(header)] + [len(c) for _, c in body]) if body else len(header)
    names, seen = [], {}
    for j in range(width):
        name = header[j] if j < len(header) and header[j] else f'열{j + 1}'
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f'{name} ({seen[name]})')
    header_key = [_norm(c) for c in header]
    data, numbers = [], []
    for number, cells in body:
        cells = (cells + [''] * width)[:width]
        if [_norm(c) for c in cells[:len(header)]] == header_key:
            continue   # the header repeated on a later page of the export
        data.append(cells)
        numbers.append(number)
    frame = pd.DataFrame(data, columns=names, dtype=str) if data else pd.DataFrame(columns=names, dtype=str)
    keep = [n for j, n in enumerate(names) if not n.startswith('열') or (data and any(row[j] for row in data))]
    frame = frame[keep].fillna('')
    frame.attrs['header_row'] = header_number - 1
    frame.attrs['source_rows'] = numbers
    return frame


def read_prescription_table(raw, max_rows, aliases, date_aliases):
    """Return one sheet of the export as text, with the header row found and original row numbers kept."""
    limit = HEADER_SCAN + max_rows + 1
    grids = [(name, rows) for name, rows in _grids(raw, limit) if len(rows) >= 2]
    if not grids:
        raise TableError('표에서 열 이름과 처방 줄을 찾지 못했습니다. 첫 줄(또는 제목 아래 줄)에 열 이름이 있고, 그 아래에 처방이 한 줄씩 있어야 합니다.')
    frames = [(name, _frame(rows, aliases)) for name, rows in grids]
    frames = [(name, f) for name, f in frames if len(f)]
    if not frames:
        raise TableError('열 이름 아래에 처방 줄이 없습니다.')
    if len(frames) > 1:
        dated = [(name, f) for name, f in frames if any(_norm(c) in date_aliases for c in f.columns)]
        if len(dated) == 1:
            frames = dated
        else:
            largest = max(len(f) for _, f in frames)
            big = [i for i, (_, f) in enumerate(frames) if len(f) == largest]
            if len(big) == 1 and all(len(f) <= 3 for i, (_, f) in enumerate(frames) if i != big[0]):
                frames = [frames[big[0]]]   # a short help or summary sheet next to the data
            else:
                names = ', '.join(name or '시트' for name, _ in frames)
                raise TableError(f'처방이 들어 있는 시트가 여러 개입니다({names}). 분석할 처방 시트 하나만 남기고 저장한 뒤 올려 주세요.')
    frame = frames[0][1]
    if len(frame) > max_rows:
        raise TableError(f'한 번에 처방 {max_rows:,}행까지 계산합니다(지금 {max_rows:,}행 초과). 환자별로 파일을 나눠 차례로 올려 주세요.')
    return frame
