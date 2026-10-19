from datetime import date, time
from typing import Optional

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.work_report import ReportType


class DailyEntryIn(BaseModel):
    work_date: date
    start_time: Optional[time] = None
    finish_time: Optional[time] = None
    description: Optional[str] = Field(None, max_length=2000)
    is_day_off: bool = False
    work_minutes: Optional[int] = Field(None, ge=0, le=1440)
    count_1: Optional[int] = Field(None, ge=0, le=100000)
    count_2: Optional[int] = Field(None, ge=0, le=100000)


class MonthlyReportUpdateIn(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    week_1: Optional[str] = Field(None, max_length=4000)
    week_2: Optional[str] = Field(None, max_length=4000)
    week_3: Optional[str] = Field(None, max_length=4000)
    week_4: Optional[str] = Field(None, max_length=4000)
    week_5: Optional[str] = Field(None, max_length=4000)
    days: list[DailyEntryIn] = Field(default_factory=list)
    condition_1_label: Optional[str] = Field(None, max_length=100)
    condition_2_label: Optional[str] = Field(None, max_length=100)


class MonthlyReportSubmitIn(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)


class ReportReviewIn(BaseModel):
    review_note: Optional[str] = Field(None, max_length=4000)
    stipend_amount: Optional[int] = Field(None, ge=0, le=10_000_000)


class MonthlyReportCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    report_type: ReportType = ReportType.HOURLY
    condition_1_label: Optional[str] = Field(None, max_length=100)
    condition_2_label: Optional[str] = Field(None, max_length=100)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nom bo'sh bo'lmasligi kerak")
        return v

    @model_validator(mode="after")
    def check_output_fields(self):
        if self.report_type is ReportType.OUTPUT:
            if not (self.condition_1_label and self.condition_1_label.strip()):
                raise ValueError("OUTPUT turida condition_1_label majburiy")
        return self
