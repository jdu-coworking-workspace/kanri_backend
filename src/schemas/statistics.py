from typing import List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

class KPIOverviewSchema(BaseModel):
    total_students: int
    total_projects: int
    active_projects: int
    done_projects: int
    working_students: int
    working_rate_percent: float
    top_skill_rank: str
    completion_rate_percent: float
    avg_students_per_project: float
    unassigned_students_count: int
    unassigned_projects_count: int
    graduated_students_count: int

class ProjectStatusBreakdownSchema(BaseModel):
    status: str
    label: str
    count: int
    percentage: float

class SkillRankBreakdownSchema(BaseModel):
    rank: str
    count: int

class SemesterBreakdownSchema(BaseModel):
    semester: str
    label: str
    count: int

class WorkStatusBreakdownSchema(BaseModel):
    status: str
    label: str
    count: int

class CategoryBreakdownSchema(BaseModel):
    category: str
    label: str
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
    points: int

class UnassignedStudentItemSchema(BaseModel):
    id: str
    full_name: str
    student_code: str
    email: str
    avatar_url: Optional[str] = None
    skill_rank: Optional[str] = None
    semester: Optional[str] = None

class StaffWorkloadItemSchema(BaseModel):
    staff_id: str
    staff_name: str
    staff_email: str
    projects_count: int
    active_projects_count: int
    managed_students_count: int

class MonthlyTrendItemSchema(BaseModel):
    month: str
    month_label: str
    new_students: int
    created_projects: int
    completed_projects: int

class StatisticsSummarySchema(BaseModel):
    kpi: KPIOverviewSchema
    project_statuses: List[ProjectStatusBreakdownSchema]
    skill_ranks: List[SkillRankBreakdownSchema]
    semesters: List[SemesterBreakdownSchema]
    work_statuses: List[WorkStatusBreakdownSchema]
    categories: List[CategoryBreakdownSchema]
    top_students: List[TopStudentItemSchema]
    unassigned_students_list: List[UnassignedStudentItemSchema]
    staff_workloads: List[StaffWorkloadItemSchema]
    monthly_trends: List[MonthlyTrendItemSchema]
