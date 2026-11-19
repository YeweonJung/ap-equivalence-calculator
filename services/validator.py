ALLOWED_EXTENSIONS = {
    "csv",
    "xls",
    "xlsx"
}

MAX_FILE_SIZE_MB = 100


def allowed_file(filename):

    if "." not in filename:
        return False

    ext = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )

    return (
        ext in ALLOWED_EXTENSIONS
    )


def validate_file(file):

    if not file:
        raise ValueError(
            "파일을 선택해 주세요."
        )

    if not allowed_file(
        file.filename
    ):
        raise ValueError(
            "CSV 또는 Excel 파일(.csv, .xlsx, .xls)을 올려 주세요."
        )

    return True
