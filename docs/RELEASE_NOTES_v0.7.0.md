# Fynvo v0.7.0 Release Notes

## Financial Calendar & Category Management

Fynvo v0.7.0 makes the product feel like a cohesive financial application rather than separate management screens.

## Highlights

- New visual direction based on the approved Fynvo dashboard mock-up.
- Modern dark navy sidebar with grouped navigation.
- Redesigned Overview dashboard with real financial data and forecast KPIs.
- Cash Flow Forecast card using v0.6.0 Baseline and Expected forecasts.
- Financial Calendar with Month, Week and Day views.
- Calendar events for income, recurring expenses, bills, Planned Spending and expected forecast events.
- Calendar and Cash Flow event drill-down.
- Quick Add for common records.
- Category visibility foundation across modules.
- Responsive layout improvements for Home Assistant ingress, tablet and mobile.

## Scope boundaries

This release does not implement full budgeting, CSV reconciliation, saved scenario management, Open Banking/CDR, advanced reports or financial-health insights. Those remain in the roadmap.

## Upgrade notes

No destructive data migration is required. Existing accounts, transactions, income, recurring expenses, bills, Planned Spending, forecast configuration and effective-dated changes remain intact.

## Manual test path

```text
Home Assistant
→ Fynvo
→ Overview
→ Cash Flow
→ Calendar
→ Month / Week / Day
→ Event drill-down
→ Quick Add
→ Categories
→ Existing Accounts / Transactions / Income / Bills / Planned Spending
```
