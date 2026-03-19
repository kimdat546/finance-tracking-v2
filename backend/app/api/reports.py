"""Reports and analytics API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.dashboard_service import DashboardService
from app.services.monthly_report_service import MonthlyReportService
from app.services.net_worth_service import NetWorthService
from app.services.trends_service import TrendsService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Dashboard summary for the current month."""
    svc = DashboardService(session)
    return await svc.get_summary(user_id)


@router.get("/dashboard/quick-stats")
async def get_quick_stats(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Quick stats for header cards."""
    svc = DashboardService(session)
    return await svc.get_quick_stats(user_id)


@router.get("/dashboard/account-balances")
async def get_account_balances(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> list:
    """All accounts with current balance."""
    svc = DashboardService(session)
    return await svc.get_account_balances(user_id)


@router.get("/dashboard/net-worth")
async def get_net_worth_dashboard(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Net worth from dashboard service."""
    svc = DashboardService(session)
    return await svc.get_net_worth(user_id)


@router.get("/monthly")
async def get_monthly_report(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    year: int = Query(default=0),
    month: int = Query(default=0),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Monthly income/expense report."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if not year:
        year = now.year
    if not month:
        month = now.month
    svc = MonthlyReportService(session)
    return await svc.get_monthly_report(user_id, year, month)


@router.get("/monthly/comparison")
async def get_monthly_comparison(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    months: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_db),
) -> list:
    """Monthly comparison for the last N months."""
    svc = MonthlyReportService(session)
    return await svc.get_monthly_comparison(user_id, months)


@router.get("/trends/categories")
async def get_category_trends(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    months: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_db),
) -> list:
    """Category spending trends over N months."""
    svc = TrendsService(session)
    return await svc.get_category_trends(user_id, months)


@router.get("/trends/anomalies")
async def get_anomalies(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> list:
    """Detected spending anomalies."""
    svc = TrendsService(session)
    return await svc.detect_anomalies(user_id)


@router.get("/trends/recurring")
async def get_recurring_transactions(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> list:
    """Detected recurring transactions."""
    svc = TrendsService(session)
    return await svc.get_recurring_transactions(user_id)


@router.get("/net-worth")
async def get_current_net_worth(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Current net worth snapshot."""
    svc = NetWorthService(session)
    return await svc.get_current_net_worth(user_id)


@router.get("/net-worth/history")
async def get_net_worth_history(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    months: int = Query(default=12, ge=1, le=60),
    session: AsyncSession = Depends(get_db),
) -> list:
    """Net worth history over N months."""
    svc = NetWorthService(session)
    return await svc.get_net_worth_history(user_id, months)
