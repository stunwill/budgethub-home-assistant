# Fynvo v0.6.0 Release Notes

## Cash Flow Forecasting

Fynvo can now project household finances forward using current balances, income, recurring expenses, bills and Planned Spending.

## Added

- Baseline cash-flow forecast.
- Expected forecast with historical run-rate estimates.
- Chronological forecast timeline.
- Projected balance after every forecast event.
- Lowest projected balance.
- Shortfall detection.
- Effective-dated amount changes for income and recurring expenses.
- Forecast drill-down API.
- Scenario comparison API.
- Dashboard 30-day forecast summary.
- Documentation for Actual, Committed, Planned, Budget and Forecast concepts.

## Changed

- Dashboard summaries now include a 30-day forecast balance.
- The roadmap now captures future financial calendar, advanced budgeting, rollover budgets, sinking funds, transaction import, CDR/Open Banking, recurring-transaction intelligence, Planned vs Actual matching, Home Assistant sensors and long-term forecast intelligence.

## Known limitations

- Scenario persistence is architecturally prepared but not exposed as a full scenario-management UI.
- Historical run-rate forecasting is deliberately conservative and excludes categories already represented by known commitments.
- Budgeting remains planned for v0.8.0.
- CSV reconciliation and CDR/Open Banking remain future releases.
