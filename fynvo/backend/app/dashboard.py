from .config import get_settings
from .schemas import DashboardResponse, DashboardSummary


def get_overview(range_days: int = 90) -> DashboardResponse:
    settings = get_settings()
    return DashboardResponse(
        summary=DashboardSummary(currency=settings.default_currency, range_days=range_days),
        upcoming=[],
        top_planned_spending=[],
        quick_stats=[],
        empty_state=(
            "Fynvo is ready for your first accounts, income, recurring expenses and planned spending. "
            "Future releases will populate this dashboard with real financial data."
        ),
    )
