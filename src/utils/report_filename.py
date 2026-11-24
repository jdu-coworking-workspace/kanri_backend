import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

TASHKENT = timezone(timedelta(hours=5))  # O'zbekistonda yozgi/qishki vaqt yo'q


def _safe_part(value) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", value or "")
    return re.sub(r"\s+", "_", cleaned.strip())


def _today(now=None) -> tuple[str, str, str]:
    now = now or datetime.now(TASHKENT)
    return str(now.year), f"{now.month:02d}", f"{now.day:02d}"


def report_filename(report: dict, extension: str = "xlsx", now=None) -> str:
    """{student_code}_{yil}_{oy}_{kun}_{student_ismi}_{hisobot_turi}.{extension}
    Sana = yuklab olingan sana (Toshkent vaqti)."""
    year, month, day = _today(now)
    code = _safe_part(report.get("student_code")) or "student"
    name = _safe_part(report.get("student_name")) or "report"
    kind = _safe_part(report.get("report_type")) or "report"
    return f"{code}_{year}_{month}_{day}_{name}_{kind}.{extension}"


def archive_filename(now=None) -> str:
    year, month, day = _today(now)
    return f"reports_{year}_{month}_{day}.zip"


def content_disposition(filename: str) -> str:
    """Yapon harflari va bo'sh joyli nomlar to'g'ri ko'rinishi uchun filename* ishlatiladi."""
    fallback = re.sub(r"[^\x20-\x7e]", "_", filename).replace('"', "")
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"