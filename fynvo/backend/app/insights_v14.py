"""Canonical v0.14 Insights API wiring.

The core Insights service is kept separate from the shared `/api` router so the
service can be reused by Dashboard aggregation without duplicating financial
calculations. This adapter exposes it at `/api/insights` through `v09.router`.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .insights import (
    dismiss_insight,
    financial_health,
    generate_insights,
    insight_detail,
    list_insights,
    mark_reviewed,
)
from .models import User

router = APIRouter(prefix="/insights")
DB = Depends(get_db)
USER = Depends(get_current_user)


@router.post("/refresh")
def refresh_insights_v14(
    horizon_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    return generate_insights(db, current_user, horizon_days)


@router.get("")
def list_insights_v14(
    insight_status: str = Query("current", alias="status"),
    importance: str | None = None,
    category: str | None = None,
    horizon_days: int = Query(90, ge=7, le=365),
    refresh: bool = True,
    db: DbSession = DB,
    current_user: User = USER,
):
    return list_insights(
        insight_status=insight_status,
        importance=importance,
        category=category,
        horizon_days=horizon_days,
        refresh=refresh,
        db=db,
        current_user=current_user,
    )


@router.get("/financial-health")
def financial_health_v14(
    horizon_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    return financial_health(db, current_user, horizon_days, True)


@router.get("/{insight_id}")
def insight_detail_v14(
    insight_id: int,
    db: DbSession = DB,
    current_user: User = USER,
):
    return insight_detail(insight_id, db, current_user)


@router.post("/{insight_id}/reviewed")
def mark_reviewed_v14(
    insight_id: int,
    db: DbSession = DB,
    current_user: User = USER,
):
    return mark_reviewed(insight_id, db, current_user)


@router.post("/{insight_id}/dismiss")
def dismiss_insight_v14(
    insight_id: int,
    db: DbSession = DB,
    current_user: User = USER,
):
    return dismiss_insight(insight_id, db, current_user)
