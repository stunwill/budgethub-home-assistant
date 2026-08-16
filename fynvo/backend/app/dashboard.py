from .schemas import DashboardResponse, DashboardSummary


def get_overview(range_days: int = 90) -> DashboardResponse:
    return DashboardResponse(
        summary=DashboardSummary(
            income="0.00",
            recurring_bills="0.00",
            planned_spending="0.00",
            projected_balance="0.00",
            available_cash="0.00",
            net_position="0.00",
            assets="0.00",
            liabilities="0.00",
            account_count=0,
            range_days=range_days,
        ),
        upcoming=[],
        top_planned_spending=[],
        quick_stats=[],
        recent_transactions=[],
        empty_state="Add accounts and transactions to begin building your financial ledger.",
    )
