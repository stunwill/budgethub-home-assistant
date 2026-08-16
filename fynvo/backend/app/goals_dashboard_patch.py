from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .goals import command_centre_dashboard
from .intelligence import ensure_intelligence_schema
from .models import User

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)


@router.get("/dashboard/command-centre")
def command_centre_dashboard_with_intelligence_schema(
    range_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    ensure_intelligence_schema(db)
    return command_centre_dashboard(range_days=range_days, db=db, current_user=current_user)
