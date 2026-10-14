from datetime import date, time
from typing import Optional

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class DailyEntryIn(BaseModel):
    work_date: date
    start_time: Optional[time] = None
    finish_time: Optional[time] = None
    description: Optional[str] = Field(None, max_length=2000)
    is_day_off: bool = False


class MonthlyReportUpdateIn(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    week_1: Optional[str] = Field(None, max_length=4000)
    week_2: Optional[str] = Field(None, max_length=4000)
    week_3: Optional[str] = Field(None, max_length=4000)
    week_4: Optional[str] = Field(None, max_length=4000)
    week_5: Optional[str] = Field(None, max_length=4000)
    days: list[DailyEntryIn] = Field(default_factory=list)


class MonthlyReportSubmitIn(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)


class ReportReviewIn(BaseModel):
    review_note: Optional[str] = Field(None, max_length=4000)
    stipend_amount: Optional[int] = Field(None, ge=0, le=10_000_000)
