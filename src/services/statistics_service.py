from typing import Optional
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import case, func, select

from src.models.student import Student, SkillRank
from src.models.project import Project, ProjectStatus
from src.models.project_member import ProjectMember
from src.schemas.statistics import (
    KPIOverviewSchema,
    SkillRankBreakdownSchema,
    TopStudentItemSchema,
    StatisticsSummarySchema,
)

TOP_STUDENTS_LIMIT = 5

# S highest … E lowest; null ranks last
SKILL_RANK_PRIORITY = case(
    (Student.skill_rank == SkillRank.S, 1),
    (Student.skill_rank == SkillRank.A, 2),
    (Student.skill_rank == SkillRank.B, 3),
    (Student.skill_rank == SkillRank.C, 4),
    (Student.skill_rank == SkillRank.D, 5),
    (Student.skill_rank == SkillRank.E, 6),
    else_=7,
)


class StatisticsService:
    @staticmethod
    def get_summary(
        db: Session,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> StatisticsSummarySchema:
        # --- Projects (optional filters; unused by current UI) ---
        project_query = db.query(Project)

        if status_filter and status_filter != "all":
            project_query = project_query.filter(Project.status == status_filter)

        if category_filter and category_filter != "all":
            project_query = project_query.filter(Project.category == category_filter)

        total_projects = project_query.count()
        active_projects = project_query.filter(
            Project.status == ProjectStatus.ACTIVE
        ).count()

        # --- Students (global) ---
        total_students = db.query(Student).count()

        assigned_on_active_subq = (
            db.query(ProjectMember.student_id)
            .join(Project, Project.id == ProjectMember.project_id)
            .filter(
                ProjectMember.left_at.is_(None),
                Project.status == ProjectStatus.ACTIVE,
            )
            .distinct()
            .subquery()
        )
        unassigned_students_count = (
            db.query(Student)
            .filter(Student.id.not_in(select(assigned_on_active_subq)))
            .count()
        )

        kpi = KPIOverviewSchema(
            total_students=total_students,
            total_projects=total_projects,
            active_projects=active_projects,
            unassigned_students_count=unassigned_students_count,
        )

        # --- Skill ranks ---
        rank_counts_raw = (
            db.query(Student.skill_rank, func.count(Student.id))
            .group_by(Student.skill_rank)
            .all()
        )
        rank_dict = {
            (r.value if hasattr(r, "value") else str(r)): count
            for r, count in rank_counts_raw
            if r is not None
        }
        skill_ranks = [
            SkillRankBreakdownSchema(rank=r.value, count=rank_dict.get(r.value, 0))
            for r in SkillRank
        ]

        # --- Top students: more active projects first, then better skill rank (S→E) ---
        active_memberships_subq = (
            db.query(
                ProjectMember.student_id,
                func.count(ProjectMember.id).label("active_projects_count"),
            )
            .join(Project, Project.id == ProjectMember.project_id)
            .filter(
                ProjectMember.left_at.is_(None),
                Project.status == ProjectStatus.ACTIVE,
            )
            .group_by(ProjectMember.student_id)
            .subquery()
        )

        active_count_col = func.coalesce(
            active_memberships_subq.c.active_projects_count, 0
        )

        top_students_raw = (
            db.query(Student, active_count_col.label("active_projects_count"))
            .outerjoin(
                active_memberships_subq,
                Student.id == active_memberships_subq.c.student_id,
            )
            .order_by(active_count_col.desc(), SKILL_RANK_PRIORITY.asc())
            .limit(TOP_STUDENTS_LIMIT)
            .all()
        )

        top_students = [
            TopStudentItemSchema(
                id=str(student.id),
                full_name=student.full_name,
                student_code=student.student_code,
                email=student.email,
                avatar_url=student.avatar_url,
                skill_rank=student.skill_rank.value if student.skill_rank else None,
                semester=student.semester.value if student.semester else None,
                active_projects_count=active_count,
            )
            for student, active_count in top_students_raw
        ]

        return StatisticsSummarySchema(
            kpi=kpi,
            skill_ranks=skill_ranks,
            top_students=top_students,
        )
