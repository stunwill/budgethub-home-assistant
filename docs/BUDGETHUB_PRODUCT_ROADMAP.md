# BudgetHub Product Roadmap

This roadmap is the canonical development queue for BudgetHub.

## Product principles

1. Forecast actual dated cash flow, not just monthly averages.
2. Keep financial data local by default.
3. Make scenario planning simple enough for everyday household use.
4. Separate planned spending from recurring commitments.
5. Build the financial engine independently of Home Assistant recorder/history.
6. Prefer clear, auditable calculations over opaque automation.

## v0.1.0 - Foundation

### Application foundation
- [ ] Home Assistant add-on packaging
- [ ] FastAPI backend
- [ ] React/Vite frontend
- [ ] SQLite persistence under `/data`
- [ ] Australia/Melbourne timezone
- [ ] AUD currency formatting
- [ ] health endpoint
- [ ] application version endpoint

### Recurring expenses
- [ ] Create, edit and archive recurring expenses
- [ ] Name
- [ ] Amount
- [ ] Category
- [ ] Frequency
- [ ] Next due date
- [ ] Notes
- [ ] Supported frequencies: weekly, fortnightly, monthly, quarterly, six-monthly, annually and custom

### Income
- [ ] Create, edit and archive recurring income
- [ ] Source/name
- [ ] Amount
- [ ] Frequency
- [ ] Next payment date
- [ ] Notes
- [ ] Support irregular/manual income

### Planned spending
- [ ] Create, edit and archive planned purchases
- [ ] Description
- [ ] Estimated amount
- [ ] Optional planned date
- [ ] Priority
- [ ] Status: Wishlist, Planned, Purchased, Cancelled
- [ ] Include/exclude toggle for forecast
- [ ] Undated wishlist items do not affect forecast

### Cash-flow forecast
- [ ] Generate future occurrences from recurrence rules
- [ ] Combine income, expenses and dated planned spending
- [ ] Running projected balance
- [ ] 30, 60 and 90 day views
- [ ] Scenario recalculation when planned purchase dates or inclusion change

### Dashboard
- [ ] Current/starting balance input
- [ ] Upcoming income
- [ ] Upcoming bills
- [ ] Planned spending
- [ ] Projected balance
- [ ] Cash-flow chart
- [ ] Upcoming transactions list

## v0.2.0 - Calendar and categories
- [ ] Monthly calendar view
- [ ] Category management
- [ ] Category filters
- [ ] Search and filtering
- [ ] Calendar transaction detail modal
- [ ] Custom recurring schedules

## v0.3.0 - Provisioning and sinking funds
- [ ] Annual/irregular bill provisioning
- [ ] Suggested weekly, fortnightly and monthly set-aside amounts
- [ ] Sinking funds
- [ ] Funding progress
- [ ] Due-date warnings

## v0.4.0 - Actual spending and budget comparison
- [ ] Actual transactions
- [ ] Budgeted vs actual reporting
- [ ] Monthly category budgets
- [ ] Variance reporting
- [ ] Manual transaction import
- [ ] CSV import/export

## v0.5.0 - Savings and goals
- [ ] Savings goals
- [ ] Target dates
- [ ] Required contribution calculations
- [ ] Goal priority
- [ ] Planned purchase linked to savings goal

## v0.6.0 - Household insights
- [ ] Monthly and annual reports
- [ ] Income/expense trends
- [ ] Recurring-cost change history
- [ ] Forecast low-balance warnings
- [ ] What-if scenarios with multiple alternatives

## Future integrations
- [ ] Google Sheets export
- [ ] Optional transaction import integrations
- [ ] Home Assistant sensors for key BudgetHub metrics
- [ ] Notifications for upcoming large expenses
- [ ] Integration with household spending tracking

## Explicitly deferred from v0.1.0

- Bank account connections
- Open Banking feeds
- Credit-card feeds
- Google Sheets dependency
- Automated financial advice
- Multi-currency support
