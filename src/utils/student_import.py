"""Talabalarni ommaviy import qilish uchun fayl parseri.

Qo'llab-quvvatlanadigan formatlar:
- ``.xlsx`` (openpyxl orqali, birinchi worksheet)
- ``.csv`` (UTF-8, UTF-8 BOM yoki Shift-JIS/CP932)

Parser faqat faylni ``List[Dict[str, Any]]`` ga aylantiradi. Har bir qatorga
fayldagi haqiqiy qator raqami ``row`` kaliti bilan qo'shiladi, shunda
validatsiya xatolari admin uchun tushunarli bo'ladi.
"""
import csv
import re
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional
from zipfile import BadZipFile

# pyrefly: ignore [missing-import]
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "student_templates"
TEMPLATE_XLSX = TEMPLATE_DIR / "students.xlsx"
TEMPLATE_CSV = TEMPLATE_DIR / "students.csv"

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 500

REQUIRED_COLUMNS = ("full_name", "kana_name", "student_code", "email")
OPTIONAL_COLUMNS = (
    "grad_year_month",
    "semester",
    "skill_rank",
    "work_status",
)
ALLOWED_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# Excel/CSV fayllarda uchraydigan muqobil sarlavhalar.
HEADER_ALIASES = {
    "氏名": "full_name",
    "名前": "full_name",
    "full name": "full_name",
    "fullname": "full_name",
    "フリガナ": "kana_name",
    "カナ": "kana_name",
    "かな": "kana_name",
    "学籍番号": "student_code",
    "学生番号": "student_code",
    "student id": "student_code",
    "studentid": "student_code",
    "メールアドレス": "email",
    "email address": "email",
    "e-mail": "email",
    "e_mail": "email",
    "卒業年月": "grad_year_month",
    "卒業年月日": "grad_year_month",
    "graduation": "grad_year_month",
    "graduation date": "grad_year_month",
    "学期": "semester",
    "セメスター": "semester",
    "スキルランク": "skill_rank",
    "ランク": "skill_rank",
    "ステータス": "work_status",
    "勤務状況": "work_status",
}

CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp932", "shift_jis")


class StudentFileError(Exception):
    """Fayl formati yoki tarkibi bilan bog'liq xatolik."""

    def __init__(self, code: str, message: str, errors: Optional[List[dict]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.errors = errors or []


def _normalize_header(raw: Any) -> str:
    if raw is None:
        return ""
    key = str(raw).strip()
    if not key:
        return ""
    lowered = key.lower()
    if lowered in HEADER_ALIASES:
        return HEADER_ALIASES[lowered]
    if key in HEADER_ALIASES:
        return HEADER_ALIASES[key]
    return lowered.replace(" ", "_").replace("-", "_")


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _normalize_date(value: Any) -> Optional[str]:
    if _is_empty(value):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Excel sana seriyasi (1900 sana tizimi)
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()

    text = str(value).strip().replace("/", "-").replace(".", "-")
    match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-01"
    return text


def _normalize_semester(value: Any) -> Optional[str]:
    if _is_empty(value):
        return None
    text = str(value).strip()
    if text.lower() in ("卒業", "graduated", "graduate"):
        return "卒業"
    match = re.fullmatch(r"(\d+)\s*(?:semestr|semester|学期|セメスター)?", text, re.IGNORECASE)
    if match:
        return f"{int(match.group(1))}-semestr"
    return text


def _normalize_skill_rank(value: Any) -> Optional[str]:
    if _is_empty(value):
        return None
    return str(value).strip().upper()


def _normalize_work_status(value: Any) -> Optional[str]:
    if _is_empty(value):
        return None
    return re.sub(r"[\s-]+", "_", str(value).strip().lower())


def _normalize_student_code(value: Any) -> Optional[str]:
    if _is_empty(value):
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def _normalize_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for key, value in raw.items():
        if key == "student_code":
            row[key] = _normalize_student_code(value)
        elif key == "grad_year_month":
            row[key] = _normalize_date(value)
        elif key == "semester":
            row[key] = _normalize_semester(value)
        elif key == "skill_rank":
            row[key] = _normalize_skill_rank(value)
        elif key == "work_status":
            row[key] = _normalize_work_status(value)
        elif isinstance(value, str):
            row[key] = value.strip() or None
        else:
            row[key] = value
    return row


def _build_rows(header: List[str], data_rows: List[tuple]) -> List[Dict[str, Any]]:
    """Header va (qator raqami, qiymatlar) juftliklaridan dict ro'yxati yasaydi."""
    if not header:
        raise StudentFileError(
            "EMPTY_FILE",
            "Fayl bo'sh: sarlavha qatori topilmadi",
        )

    normalized = [_normalize_header(cell) for cell in header]
    present = [name for name in normalized if name]
    unknown = [name for name in present if name not in ALLOWED_COLUMNS]
    if unknown:
        raise StudentFileError(
            "UNKNOWN_COLUMNS",
            "Faylda noma'lum ustunlar bor",
            [{"row": 1, "errors": [f"Noma'lum ustun: {name}" for name in unknown]}],
        )

    missing = [name for name in REQUIRED_COLUMNS if name not in present]
    if missing:
        raise StudentFileError(
            "MISSING_COLUMNS",
            "Faylda majburiy ustunlar yetishmaydi",
            [{"row": 1, "errors": [f"Majburiy ustun topilmadi: {name}" for name in missing]}],
        )

    rows: List[Dict[str, Any]] = []
    for row_no, values in data_rows:
        if all(_is_empty(value) for value in values):
            continue
        raw: Dict[str, Any] = {}
        for idx, name in enumerate(normalized):
            if not name:
                continue
            raw[name] = values[idx] if idx < len(values) else None
        normalized_row = _normalize_row(raw)
        normalized_row["row"] = row_no
        rows.append(normalized_row)

    if not rows:
        raise StudentFileError(
            "EMPTY_FILE",
            "Faylda ma'lumot qatorlari topilmadi",
        )
    if len(rows) > MAX_ROWS:
        raise StudentFileError(
            "TOO_MANY_ROWS",
            f"Bir martada ko'pi bilan {MAX_ROWS} ta talaba qo'shish mumkin",
            [{"row": 0, "errors": [f"Faylda {len(rows)} ta qator bor"]}],
        )
    return rows


def _parse_csv(content: bytes) -> List[Dict[str, Any]]:
    text: Optional[str] = None
    for encoding in CSV_ENCODINGS:
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise StudentFileError(
            "INVALID_ENCODING",
            "CSV fayl kodlashini o'qib bo'lmadi. UTF-8 formatida saqlang",
        )

    reader = csv.reader(StringIO(text))
    header: List[str] = []
    data_rows: List[tuple] = []
    for row_no, values in enumerate(reader, start=1):
        if not header:
            if all(_is_empty(value) for value in values):
                continue
            header = list(values)
            continue
        data_rows.append((row_no, list(values)))
    return _build_rows(header, data_rows)


def _parse_xlsx(content: bytes) -> List[Dict[str, Any]]:
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, OSError, ValueError, KeyError, TypeError):
        raise StudentFileError(
            "INVALID_FILE",
            "XLSX faylni o'qib bo'lmadi. Fayl buzilgan bo'lishi mumkin",
        )

    try:
        sheet = workbook.active
        header: List[str] = []
        data_rows: List[tuple] = []
        for row_no, values in enumerate(sheet.iter_rows(values_only=True), start=1):
            values = list(values)
            if not header:
                if all(_is_empty(value) for value in values):
                    continue
                header = values
                continue
            data_rows.append((row_no, values))
    except (BadZipFile, OSError, ValueError, KeyError, TypeError):
        raise StudentFileError(
            "INVALID_FILE",
            "XLSX faylni o'qib bo'lmadi. Fayl buzilgan bo'lishi mumkin",
        )
    finally:
        workbook.close()

    return _build_rows(header, data_rows)


def parse_student_file(filename: str, content: bytes) -> List[Dict[str, Any]]:
    """Faylni kengaytmasiga qarab parse qiladi va qatorlar ro'yxatini qaytaradi."""
    if not content:
        raise StudentFileError("EMPTY_FILE", "Yuklangan fayl bo'sh")

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".csv":
        return _parse_csv(content)
    if suffix == ".xlsx":
        return _parse_xlsx(content)
    raise StudentFileError(
        "INVALID_FILE_TYPE",
        "Faqat .xlsx yoki .csv fayl yuklash mumkin",
    )


def read_template(file_format: str) -> tuple[bytes, str, str]:
    """Template fayl baytlarini, MIME type va fayl nomini qaytaradi."""
    if file_format == "xlsx":
        path = TEMPLATE_XLSX
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_format == "csv":
        path = TEMPLATE_CSV
        media_type = "text/csv; charset=utf-8"
    else:
        raise StudentFileError(
            "INVALID_TEMPLATE_FORMAT",
            "Template formati faqat xlsx yoki csv bo'lishi mumkin",
        )

    if not path.exists():
        raise StudentFileError(
            "TEMPLATE_NOT_FOUND",
            "Template fayl topilmadi",
        )
    return path.read_bytes(), media_type, path.name
