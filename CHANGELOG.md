# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v0.6.0

### Added
- Added reusable cash-flow forecasting engine.
- Added Baseline Forecast using current balances, income, recurring expenses, bills and Planned Spending.
- Added Expected Forecast with historical run-rate spending estimates where enough transaction history exists.
- Added chronological forecast timeline with projected balance after each event.
- Added lowest projected balance and projected shortfall detection.
- Added effective-dated amount changes for recurring income and recurring expenses.
- Added forecast drill-down API for month/day grouped forecast records.
- Added lightweight what-if scenario comparisons that do not modify real records.
- Added forecast chart data for balance-over-time visualisation.
- Added dashboard forecast balance and lowest-balance summary.
- Added cash-flow forecasting documentation and v0.6.0 release notes.

### Changed
- Updated Fynvo version references to v0.6.0.
- Expanded the product roadmap with financial calendar, advanced budgeting, rollover budgets, sinking funds, import/reconciliation, CDR/Open Banking, recurring intelligence, Planned vs Actual matching, Home Assistant sensors and forecast intelligence.
- Clarified Actual, Committed, Planned, Budget and Forecast as separate Fynvo product concepts.

### Fixed
- Kept scenario calculations isolated so hypothetical changes do not create or edit real financial records.
- Kept historical run-rate estimates separate from known recurring expenses, bills and Planned Spending to reduce double-counting.

### Security
- Forecast, scenario and effective-amount-change APIs require the authenticated server-side session and are scoped to the authenticated user.

## v0.5.0

### Added
- Added Planned Spending management for wishlist, planned, committed, purchased and cancelled future spending records.
- Added priority, status, category, merchant/provider, notes, account link and forecast inclusion support for planned spending.
- Added incomplete Planned Spending handling so unknown amounts and unknown dates remain pending rather than becoming `$0.00` or invented dates.
- Added Planned Spending API create, edit, cancel/archive and list/filter foundations.
- Added Planned Spending integration into Overview, Week, Month, Pay Cycle and Year financial views.
- Added enhanced Month view that breaks a calendar month into Monday-Sunday weekly columns, including partial first/final weeks.
- Added clickable weekly cells, monthly totals and annual cells so totals can be drilled down to the underlying financial records.
- Added Fynvo logo, mark and favicon assets for application branding.

### Changed
- Updated Fynvo version references to v0.5.0.
- Enhanced the annual matrix so Planned Spending can appear in scheduled financial totals when included in forecast.
- Updated Overview Top Planned Spending to use real planned-spending data.
- Updated scheduled totals to separately expose recurring commitments, bills and planned spending.

### Fixed
- Preserved the distinction between planned spending, bills and actual transactions so planned purchases do not create fake actual transactions.

### Security
- Planned Spending APIs require the authenticated server-side session and are scoped to the authenticated user.

## v0.4.0

### Added
- Added Income management for recurring and one-off income sources.
- Added Recurring Expenses with weekly, fortnightly, every-28-days, every-four-weeks, monthly, quarterly, yearly, custom and one-off recurrence support.
- Added incomplete recurring-expense tracking so records can be saved with missing amount, frequency, date or account information.
- Added Bills & Obligations for one-off bills, arrears and outstanding financial commitments.
- Added dynamic due-state calculation for upcoming, due soon, due today, overdue, paid and unknown bills.
- Added priority support for bills and obligations.
- Added paid-through date support for utility-style obligations.
- Added weekly, monthly, pay-cycle and annual schedule APIs and UI views.
- Added an Excel-style Jan-Dec annual financial matrix with clickable drill-down cells.
- Added initial household recurring-expense seed data, including incomplete and inactive records.
- Added initial outstanding bills and obligations seed data.

### Changed
- Updated Fynvo version references to v0.4.0.
- Updated the Overview dashboard to use real income, recurring-expense and bill/obligation data.
- Updated Upcoming so income, recurring expenses, bills and overdue obligations are shown chronologically.
- Preserved scheduled commitments separately from actual transactions so future CSV reconciliation can match expected vs actual without double-counting.

### Fixed
- Prevented unknown recurring-expense and bill amounts from being displayed as real `$0.00` obligations.
- Preserved unknown dates as pending/incomplete instead of inventing due dates.

### Security
- Income, recurring expense, bill and schedule APIs require the authenticated server-side session.
- Scheduled financial records are scoped to the authenticated user.

## v0.3.0

### Added
- Added account management, calculated balances, manual transactions, account-to-account transfers and dashboard financial-position data.
- Added transaction metadata foundations for future CSV import, reconciliation and recurring-cost discovery.

### Fixed
- Fixed deterministic root/SPA route handling for Home Assistant ingress.

## v0.2.0

### Added
- Fynvo foundation, authentication, local SQLite persistence and responsive Overview dashboard.
- First-run administrator setup, username/password login, server-side sessions, logout and password change.
