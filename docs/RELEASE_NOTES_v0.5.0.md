# Fynvo v0.5.0 - Planned Spending & Enhanced Financial Views

Fynvo v0.5.0 adds Planned Spending and improves financial drill-down views.

## Added

- Planned Spending management.
- Planned Spending statuses: Idea, Wishlist, Planned, Committed, Purchased and Cancelled.
- Include in Forecast toggle.
- Incomplete Planned Spending support.
- Planned Spending integration with Overview, Week, Month, Pay Cycle and Year views.
- Enhanced Month view with weekly columns and monthly totals.
- Clickable weekly, monthly and annual totals.
- Fynvo logo, mark and favicon assets.

## Changed

- Overview Planned Spending and Top Planned Spending now use real data.
- Scheduled totals now break out income, recurring commitments, bills and planned spending.
- Annual matrix includes forecast-enabled Planned Spending.

## Upgrade notes

Existing v0.4.0 data is preserved. v0.5.0 adds a new `planned_spending` table and updates the schema version to 5.

## Manual Home Assistant check

```text
Home Assistant
→ Fynvo
→ Login
→ Overview
→ Planned Spending
→ Add Planned Item
→ Edit Planned Item
→ Month View
→ Weekly Columns
→ Week Drill-down
→ Year View
→ Month Drill-down
→ Pay Cycle
```

Also verify the Fynvo logo appears clearly in the login screen, sidebar and browser/favicon surface where supported.

## Known limitations

Full budgeting, CSV reconciliation, recurring-cost discovery, predictive estimates and connected banking remain deferred to later releases.

## Next release

The next planned release is v0.6.0 Cash Flow Forecasting.
