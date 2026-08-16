# Fynvo v0.11.0 Goals & Dashboard Modernisation

v0.11.0 introduces first-class Financial Goals and replaces the sparse implementation-oriented Overview with a household financial command centre aligned to the supplied Fynvo dashboard mock-up.

## Financial Goals

Goals answer what the household is saving toward, how much is needed, how much is already allocated and whether the current contribution rate is on track.

Supported goal types:

- Savings Goal
- Target Balance Goal
- Planned Purchase Goal
- Recurring / Annual Goal
- Debt Reduction Goal where the existing account model supports it

Core fields include name, description, goal type, target amount, current amount, start date, target date, priority, contribution frequency, contribution amount, status and notes.

## Contribution calculations

Required contributions are calculated from the remaining amount and the time to the target date.

Supported contribution frequencies:

- Weekly
- Fortnightly
- Monthly

Fortnightly calculations use true 14-day periods for the period count. The calculation avoids monthly approximation when a fortnightly contribution cadence is selected.

## Goal progress

Each Goal reports:

- target amount
- current amount
- remaining amount
- percentage complete
- required contribution
- current contribution
- forecast completion date
- calculated status
- explanation

Statuses include draft, active, on track, ahead, behind, paused, completed and cancelled. The calculated status is derived from progress against the target date where enough information exists.

## Account allocations

Goals can track explicit account allocations. This prevents one savings account balance from being counted in full against multiple Goals.

Example:

- Savings account: $10,000
- Japan Goal allocation: $3,000
- Car Goal allocation: $2,000
- Unallocated savings: $5,000

## Contributions

Manual goal contributions can be recorded. The contribution model is ready for future CDR/Open Banking linkage to bank transactions or transfers without redesigning the Goal domain.

## Goal vs Budget vs Planned Spending

Goals, Budgets and Planned Spending remain separate concepts.

- A Budget controls how much may be spent.
- A Goal controls how much should be accumulated or achieved.
- Planned Spending represents expected future purchases.

Goals can be linked to Planned Spending so Fynvo understands why a planned purchase exists without treating the Goal as the purchase itself.

## What-If contributions

The What-If endpoint lets users test a contribution amount and frequency. It returns an estimated completion date and a temporary forecast scenario impact without saving the change.

## Dashboard redesign

The Overview now follows the supplied visual reference more closely:

1. Welcome header with the current user display name.
2. Shared date-range / forecast horizon selector.
3. Five KPI cards:
   - Available Cash
   - Expected Income
   - Scheduled Commitments
   - Planned Spending
   - Projected Balance
4. Cash Flow Forecast chart.
5. Forecast Summary.
6. Upcoming Commitments.
7. Upcoming next-period events.
8. Top Planned Spending with Quick Add.
9. Quick Stats.
10. Budget Overview.
11. Goals summary.
12. Spending Intelligence attention indicator.

Development-oriented panels such as release progress and editing status are removed from the household Overview.

## Dashboard data integrity

Dashboard data is produced from Fynvo services and endpoints. It does not hard-code mock-up figures.

The command-centre endpoint reuses:

- account position
- schedule summary
- forecast engine
- budgets
- planned spending
- goals
- spending intelligence suggestion counts

## Quick Add reliability

The global Quick Add now exposes better type-aware forms and surfaces backend validation detail where available. Supported records include Transaction, Income, Bill, Recurring Expense, Planned Spending and Goal.

## Privacy

Goal and dashboard calculations operate locally on the user's Fynvo data. No financial information is sent to an external analytics service.

## Known limitations

- The dashboard is substantially modernised but should still be manually checked in Home Assistant ingress across desktop, tablet and mobile.
- What-If calculations use the existing scenario forecast service and remain indicative rather than advice.
- Full scenario intelligence remains planned for v0.13.0.
- Broader financial-health Insights remain planned for v0.14.0.
