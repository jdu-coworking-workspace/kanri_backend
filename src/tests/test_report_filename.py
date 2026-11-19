from datetime import datetime

from src.utils.report_filename import TASHKENT, archive_filename, report_filename

NOW = datetime(2026, 11, 19, 10, 0, tzinfo=TASHKENT)


def test_report_filename_format():
    report = {
        "student_code": "2314067",
        "student_name": "Shoxrux Test",
        "report_type": "hourly",
    }
    assert report_filename(report, now=NOW) == "2314067_2026_11_19_Shoxrux_Test_hourly.xlsx"


def test_report_filename_removes_unsafe_characters():
    report = {"student_code": "1", "student_name": 'A/B:"C"', "report_type": "output"}
    assert report_filename(report, now=NOW) == "1_2026_11_19_ABC_output.xlsx"


def test_archive_filename():
    assert archive_filename(now=NOW) == "reports_2026_11_19.zip"