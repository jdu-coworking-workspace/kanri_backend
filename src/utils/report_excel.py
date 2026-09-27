from datetime import date
from io import BytesIO

# pyrefly: ignore [missing-import]
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def build_monthly_report_xlsx(report: dict) -> bytes:
    """成果報告書 sheet: daily rows, weekly notes, stipend, approval."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = f"{report['year']}.{report['month']:02d}"

    header_font = Font(bold=True)
    title_font = Font(bold=True, size=14)
    thin = Border(
        left=Side(style="thin", color="D0D5DD"),
        right=Side(style="thin", color="D0D5DD"),
        top=Side(style="thin", color="D0D5DD"),
        bottom=Side(style="thin", color="D0D5DD"),
    )
    header_fill = PatternFill("solid", fgColor="F2F4F7")
    wrap = Alignment(wrap_text=True, vertical="center")

    sheet["B2"] = "成果報告書（固定制）　勤務記録表"
    sheet["B2"].font = title_font
    sheet.merge_cells("B2:F2")

    sheet["B3"] = "学籍番号"
    sheet["C3"] = report.get("student_code") or ""
    sheet["E3"] = "コワークNo"
    sheet["B4"] = "氏名"
    sheet["C4"] = report.get("student_name") or ""
    for cell in ("B3", "E3", "B4"):
        sheet[cell].font = header_font

    headers = ["日付", "開始時間", "終了時間", "作業時間", "メモ", "ファシリテータメモ"]
    for index, label in enumerate(headers, start=2):
        cell = sheet.cell(6, index, label)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin
        cell.alignment = Alignment(horizontal="center")

    row_index = 7
    for day in report["days"]:
        work_date = day["work_date"]
        if isinstance(work_date, str):
            work_date = date.fromisoformat(work_date)
        sheet.cell(row_index, 2, work_date).number_format = "YYYY-MM-DD"
        if day.get("start_time"):
            sheet.cell(row_index, 3, day["start_time"])
        if day.get("finish_time"):
            sheet.cell(row_index, 4, day["finish_time"])
        minutes = day.get("duration_minutes") or 0
        if minutes:
            hours_cell = sheet.cell(row_index, 5, round(minutes / 60, 2))
            hours_cell.number_format = "0.00"
        if day.get("is_day_off"):
            sheet.cell(row_index, 6, "休み")
        elif day.get("description"):
            sheet.cell(row_index, 6, day["description"])
        for column in range(2, 8):
            sheet.cell(row_index, column).border = thin
            sheet.cell(row_index, column).alignment = wrap
        row_index += 1

    total_row = row_index
    sheet.cell(total_row, 2, "合計").font = header_font
    total_cell = sheet.cell(total_row, 5, round((report.get("total_minutes") or 0) / 60, 2))
    total_cell.font = header_font
    total_cell.number_format = "0.00"

    week_labels = ["第1週", "第2週", "第3週", "第4週", "第5週"]
    week_row = total_row + 2
    for offset, label in enumerate(week_labels):
        sheet.cell(week_row + offset, 2, label).font = header_font
        sheet.cell(week_row + offset, 3, report.get(f"week_{offset + 1}") or "")
        sheet.merge_cells(
            start_row=week_row + offset,
            start_column=3,
            end_row=week_row + offset,
            end_column=6,
        )

    stipend_row = week_row + 6
    sheet.cell(stipend_row, 2, "支給額").font = header_font
    if report.get("stipend_amount") is not None:
        sheet.cell(stipend_row, 3, report["stipend_amount"])

    approval_row = stipend_row + 2
    sheet.cell(approval_row, 2, "月末承認").font = header_font
    status = report.get("status")
    if status == "approved":
        sheet.cell(approval_row, 3, "承認")
    elif status == "rejected":
        sheet.cell(approval_row, 3, "承認不可")
    if report.get("review_note"):
        sheet.cell(approval_row, 4, report["review_note"])

    widths = {"A": 3, "B": 14, "C": 14, "D": 14, "E": 12, "F": 42, "G": 22}
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "B7"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_title_rows = "1:6"
    sheet.oddFooter.center.text = f"{report['year']}-{report['month']:02d}"
    sheet.auto_filter.ref = f"B6:{get_column_letter(7)}{max(row_index - 1, 6)}"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
