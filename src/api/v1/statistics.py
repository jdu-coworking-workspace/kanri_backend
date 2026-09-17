import traceback
from typing import Optional
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.api.deps import get_current_user
from src.models.user import User
from src.schemas.statistics import StatisticsSummarySchema
from src.services.statistics_service import StatisticsService

router = APIRouter()

@router.get("/summary", response_model=StatisticsSummarySchema)
def get_statistics_summary(
    period: Optional[str] = Query("all", description="Period filter: all, month, year"),
    status_filter: Optional[str] = Query(None, description="Status filter: active, done, planned, cancelled"),
    category_filter: Optional[str] = Query(None, description="Category filter: it, video, light_work, trial"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin va Staff uchun 6-modulli statistikalar va grafik ma'lumotlarini qaytaruvchi API.
    """
    try:
        return StatisticsService.get_summary(
            db=db,
            period=period,
            status_filter=status_filter,
            category_filter=category_filter
        )
    except Exception as e:
        print("!!! ERROR IN STATISTICS ENDPOINT !!!")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
