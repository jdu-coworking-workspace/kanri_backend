from typing import Optional
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.api.deps import require_staff_or_admin
from src.models.user import User
from src.schemas.statistics import StatisticsSummarySchema
from src.services.statistics_service import StatisticsService

router = APIRouter()


@router.get("/summary", response_model=StatisticsSummarySchema)
def get_statistics_summary(
    status_filter: Optional[str] = Query(
        None, description="Status filter: all, active, done, planned, cancelled"
    ),
    category_filter: Optional[str] = Query(
        None, description="Category filter: all, it, video, light_work, trial"
    ),
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """
    Compact statistics: total students, filtered projects, unassigned count,
    skill-rank breakdown, and top active students.
    """
    try:
        return StatisticsService.get_summary(
            db=db,
            status_filter=status_filter,
            category_filter=category_filter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
