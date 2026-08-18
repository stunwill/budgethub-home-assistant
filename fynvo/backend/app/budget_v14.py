"""v0.14 correction for the Budget analysis API.

The v0.9 route passed the `mode` positional argument into `category_id`, which
could return an empty Budget analysis even though active Budgets existed.
v0.14 uses keyword arguments so Insights and the Budgeting screen reconcile to
the same calculation service.
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .budget import analyse_budgets
from .database import get_db
from .models import User
from .security import utcnow

router = APIRouter(prefix="/budgets")
DB = Depends(get_db)
USER = Depends(get_current_user)


@router.get("/analysis")
def budget_analysis_v14(
    start: date | None = None,
    end: date | None = None,
    mode: str = "native",
    current_user: User = USER,
    db: DbSession = DB,
):
    day = utcnow().date()
    return analyse_budgets(
        db,
        current_user,
        start=start or date(day.year, day.month, 1),
        end=end or day,
        mode=mode,
    )
