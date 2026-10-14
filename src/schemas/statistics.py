from typing import List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel


class KPIOverviewSchema(BaseModel):
    total_students: int
    total_projects: int
    active_projects: int
    unassigned_students_count: int


class SkillRankBreakdownSchema(BaseModel):
    rank: str
    count: int


class TopStudentItemSchema(BaseModel):
    id: str
    full_name: str
    student_code: str
    email: str
    avatar_url: Optional[str] = None
    skill_rank: Optional[str] = None
    semester: Optional[str] = None
    active_projects_count: int


class StatisticsSummarySchema(BaseModel):
    kpi: KPIOverviewSchema
    skill_ranks: List[SkillRankBreakdownSchema]
    top_students: List[TopStudentItemSchema]
