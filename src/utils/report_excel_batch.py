from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from src.utils.report_excel import build_monthly_report_xlsx
from src.utils.report_filename import report_filename


def build_period_archive(reports: list[dict], year: int, month: int) -> bytes:
    """Zip every report so the admin can grab them all at once."""
    buffer = BytesIO()
    used: set[str] = set()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for report in reports:
            base = report_filename(report)
            filename, number = base, 2
            while filename in used:
                stem, ext = base.rsplit(".", 1)
                filename = f"{stem}_{number}.{ext}"
                number += 1
            used.add(filename)
            archive.writestr(filename, build_monthly_report_xlsx(report))
    return buffer.getvalue()