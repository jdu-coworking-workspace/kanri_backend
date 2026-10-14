from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from src.utils.report_excel import build_monthly_report_xlsx


def build_period_archive(reports: list[dict], year: int, month: int) -> bytes:
    """Zip every report of one period so the admin can grab them all at once.

    Each entry uses the same official 成果報告書 template as the single
    download, so files inside the archive are identical to the ones an admin
    would get one by one.
    """
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for report in reports:
            filename = f"{report['student_code']}_{year}-{month:02d}.xlsx"
            archive.writestr(filename, build_monthly_report_xlsx(report))
    return buffer.getvalue()