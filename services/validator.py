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
            "No file uploaded."
        )

    if not allowed_file(
        file.filename
    ):
        raise ValueError(
            "Unsupported file type."
        )

    return True
