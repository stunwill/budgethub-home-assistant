# Fynvo v0.8.0 Release Notes

## Advanced Budgeting

v0.8.0 introduces Fynvo's budgeting foundation.

Budgets are now treated as first-class financial records that remain separate from transactions, recurring expenses, bills, Planned Spending and forecasts.

## Added

- Expense budgets.
- Income budget/target foundations.
- Weekly, fortnightly, monthly, quarterly and annual budget periods.
- True fortnightly budget periods anchored to a start date.
- Annual budget allocation strategies including weekly, fortnightly and monthly equivalents.
- Category hierarchy foundations.
- Parent/child budget relationship modes:
  - Independent;
  - Shared Parent Pool;
  - Parent Equals Sum of Children.
- Budget analysis showing Budget vs Actual vs Committed vs Planned vs Forecast.
- Current remaining and projected remaining calculations.
- Forecast-based budget warnings.
- Budget-period progress metrics.
- Rollover stored separately from base budget.
- Unbudgeted category detection.
- Historical average foundation for unbudgeted category review.
- Saved Views / View Preferences foundation for table layouts, sorting, filters and report settings.
- Reset View support.
- Budget documentation.

## Changed

- Version references updated to `0.8.0`.
- Roadmap updated to mark v0.8.0 as Advanced Budgeting work and keep v0.9.0 CSV Import & Reconciliation as the next release.
- Home Assistant add-on description now includes budgeting.

## Security

Budget, category and saved-view calculations are scoped to the authenticated user in the backend service layer.

## Known limitations

- The first v0.8.0 implementation focuses on backend budget correctness and reusable analysis foundations.
- Full drag-and-drop table customisation UI remains a follow-up refinement.
- Full report/export UI remains future scope.
- Home Assistant financial budget sensors remain planned for a later integration release.

## Manual verification

After merging, verify:

```text
Home Assistant
→ Fynvo
→ Login
→ Budgeting
→ Create/edit budgets
→ Review Budget Summary
→ Review unbudgeted categories
→ Create category hierarchy
→ Save/reset a view preference
→ Confirm existing Accounts / Transactions / Calendar / Forecast views still work
```
