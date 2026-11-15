import calendar
from datetime import date, datetime, time
from io import BytesIO
from pathlib import Path

# pyrefly: ignore [missing-import]
from openpyxl import load_workbook

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "seika_houkokusho.xlsx"
OUTPUT_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "seika_houkokusho_output.xlsx"
)
DAY_START_ROW = 7
MAX_DAY_SLOTS = 31
WEEK_CELLS = {
    1: "C41",
    2: "C44",
    3: "C47",
    4: "C50",
    5: "C53",
}
# 成果制 (output) template layout
OUTPUT_DAY_START_ROW = 6
OUTPUT_MAX_DAY_SLOTS = 31
OUTPUT_WEEK_CELLS = {
    1: "C40",
    2: "C43",
    3: "C46",
    4: "C49",
    5: "C52",
}
OUTPUT_UNIT_PRICE_CELLS = {1: "I41", 2: "J41"}


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_time(value) -> time:
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if not value:
        return time(0, 0)
    parts = str(value).strip().split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def set_cell(sheet, row: int, column: int, value) -> None:
    """Worksheet.cell() silently ignores a None value, so assign explicitly."""
    sheet.cell(row=row, column=column).value = value


def _minutes_as_time(minutes) -> time:
    total = max(0, min(int(minutes or 0), 24 * 60 - 1))
    return time(total // 60, total % 60)


def build_monthly_report_xlsx(report: dict) -> bytes:
    """Fill the official 成果報告書 template matching the report type.

    hourly → 固定制 (start/finish) template, output → 成果制 (deliverables) template.
    """
    if (report.get("report_type") or "hourly") == "output":
        return build_output_report_xlsx(report)
    return build_hourly_report_xlsx(report)


def build_hourly_report_xlsx(report: dict) -> bytes:
    """Fill the official 成果報告書（固定制） template the team already uses."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Excel template missing: {TEMPLATE_PATH}")

    workbook = load_workbook(TEMPLATE_PATH)
    sheet = workbook.active
    year = int(report["year"])
    month = int(report["month"])
    last_day = calendar.monthrange(year, month)[1]
    days_by_date = {_as_date(day["work_date"]): day for day in report.get("days") or []}

    sheet["C3"] = report.get("student_code") or ""
    sheet["F3"] = report.get("student_code") or ""
    sheet["C4"] = report.get("student_name") or ""

    for offset in range(MAX_DAY_SLOTS):
        row = DAY_START_ROW + offset
        day_number = offset + 1
        if day_number > last_day:
            set_cell(sheet, row, 2, None)
            set_cell(sheet, row, 3, time(0, 0))
            set_cell(sheet, row, 4, time(0, 0))
            set_cell(sheet, row, 6, None)
            continue

        work_date = date(year, month, day_number)
        day = days_by_date.get(work_date) or {}
        set_cell(sheet, row, 2, work_date)
        if day.get("is_day_off"):
            set_cell(sheet, row, 3, time(0, 0))
            set_cell(sheet, row, 4, time(0, 0))
            set_cell(sheet, row, 6, "休み")
        else:
            set_cell(sheet, row, 3, _as_time(day.get("start_time")))
            set_cell(sheet, row, 4, _as_time(day.get("finish_time")))
            set_cell(sheet, row, 6, day.get("description") or None)

    for week, cell in WEEK_CELLS.items():
        sheet[cell] = report.get(f"week_{week}") or None

    sheet["I41"] = report.get("stipend_amount")
    if report.get("status") == "approved":
        sheet["I47"] = "承認"
    elif report.get("status") == "rejected":
        sheet["I47"] = "承認不可"
    else:
        sheet["I47"] = None

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _output_sheet(workbook, month: int):
    """成果制 template ships one sheet per month; keep only the matching one."""
    title = f"{month}月"
    if title in workbook.sheetnames:
        sheet = workbook[title]
    else:
        sheet = workbook.active
        sheet.title = title
    for name in list(workbook.sheetnames):
        if name != sheet.title:
            del workbook[name]
    return sheet


def build_output_report_xlsx(report: dict) -> bytes:
    """Fill the official 成果報告書（成果制） template.

    Output reports are paid per deliverable, so days without work stay blank
    instead of being forced to a day-off marker.
    """
    if not OUTPUT_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Excel template missing: {OUTPUT_TEMPLATE_PATH}")

    workbook = load_workbook(OUTPUT_TEMPLATE_PATH)
    year = int(report["year"])
    month = int(report["month"])
    sheet = _output_sheet(workbook, month)
    last_day = calendar.monthrange(year, month)[1]
    days_by_date = {_as_date(day["work_date"]): day for day in report.get("days") or []}

    sheet["C3"] = report.get("student_code") or ""
    sheet["C4"] = report.get("student_name") or ""

    for offset in range(OUTPUT_MAX_DAY_SLOTS):
        row = OUTPUT_DAY_START_ROW + offset
        day_number = offset + 1
        if day_number > last_day:
            for column in (2, 3, 4, 5, 6, 8, 9, 10):
                set_cell(sheet, row, column, None)
            continue

        work_date = date(year, month, day_number)
        day = days_by_date.get(work_date) or {}
        set_cell(sheet, row, 2, work_date)
        if day.get("is_day_off"):
            for column in (3, 4, 5, 6, 8, 9, 10):
                set_cell(sheet, row, column, None)
            continue

        minutes = day.get("work_minutes") or 0
        set_cell(sheet, row, 3, _minutes_as_time(minutes) if minutes else None)
        set_cell(sheet, row, 4, day.get("count_1"))
        set_cell(sheet, row, 5, day.get("count_2"))
        set_cell(sheet, row, 6, day.get("description") or None)
        set_cell(sheet, row, 8, "承認" if day.get("is_approved") else None)
        set_cell(sheet, row, 9, day.get("approved_count_1"))
        set_cell(sheet, row, 10, day.get("approved_count_2"))

    for week, cell in OUTPUT_WEEK_CELLS.items():
        sheet[cell] = report.get(f"week_{week}") or None

    sheet[OUTPUT_UNIT_PRICE_CELLS[1]] = report.get("unit_price_1")
    sheet[OUTPUT_UNIT_PRICE_CELLS[2]] = report.get("unit_price_2")

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
