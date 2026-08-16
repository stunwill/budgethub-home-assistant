# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v0.8.0

### Added
- Added Advanced Budgeting foundations as a first-class domain.
- Added expense and income budget/target support.
- Added weekly, true fortnightly, monthly, quarterly and annual budget periods.
- Added annual allocation strategies for weekly, fortnightly and monthly equivalents while retaining the true annual limit.
- Added category hierarchy foundations with safe parent/child relationships and cycle prevention.
- Added parent/child budget modes: Independent, Shared Parent Pool and Parent Equals Sum of Children.
- Added budget analysis for Budget vs Actual vs Committed vs Planned vs Forecast.
- Added current remaining, projected remaining, projected variance, utilisation and period-progress metrics.
- Added rollover fields that keep base budget, rollover and effective available budget separate.
- Added unbudgeted category detection with historical-average foundations.
- Added Saved Views / View Preferences storage for table layouts, sorting, filters, account/category selections and future reporting views.
- Added Reset View support.
- Added budgeting documentation and v0.8.0 release notes.

### Changed
- Updated Fynvo version references to v0.8.0.
- Updated Home Assistant add-on metadata to include budgeting.
- Updated the roadmap to keep v0.9.0 CSV Import & Reconciliation as the next release.

### Security
- Budgeting, category hierarchy and saved-view services are scoped to the authenticated user at the service/database layer.

### Deferred
- Full visual drag-and-drop column configuration and report export remain future UI refinements.
- CSV import and reconciliation remain planned for v0.9.0.
- Full Home Assistant budget sensors remain planned for v0.15.0.

## v0.7.0

### Added
- Added the first unified Financial Calendar experience with Day, Week and Month views.
- Added calendar-based visibility for income, recurring expenses, bills, Planned Spending and forecast-generated events using the v0.6.0 forecast engine.
- Added financial event drill-down modals for projected calendar and cash-flow events.
- Added a modern Fynvo dashboard layout inspired by the approved visual mock-up.
- Added a prominent Cash Flow Forecast card with Baseline and Expected forecast lines.
- Added compact Forecast Summary, Upcoming Commitments, Top Planned Spending and Quick Stats dashboard panels.
- Added Quick Add for transactions, income, recurring expenses, bills and Planned Spending using existing APIs.
- Added Categories screen foundation that unifies category visibility across transactions, income, recurring expenses, bills and Planned Spending.
- Added reusable Fynvo design-system styling for cards, badges, navigation, calendar events, alerts, tables, modals and responsive layouts.

### Changed
- Restructured navigation into Core, Analysis and Settings groups.
- Updated desktop sidebar to use the dark navy Fynvo visual language.
- Modernised financial amount presentation, table rows, event badges and responsive layouts.
- Improved cash-shortfall presentation in the dashboard and Cash Flow views.
- Updated Fynvo version references to v0.7.0.

### Deferred
- Full Budgeting remains planned for v0.8.0.
- CSV import and reconciliation remain planned for v0.9.0.
- Saved scenario management, advanced insights and Home Assistant sensors remain future roadmap items.

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
