# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v0.10.0

### Added
- Added Spending Intelligence as a local, explainable transaction-analysis capability.
- Added merchant/payee normalisation while preserving original bank descriptions.
- Added user-managed merchant normalisation rules.
- Added user-managed categorisation rules with preview and historical application.
- Added category suggestions with confidence and supporting evidence.
- Added recurring expense detection across common cadences.
- Added recurring income detection while keeping transfers separate from ordinary income.
- Added recurring amount-change suggestions for increases and decreases.
- Added Spending Intelligence review queue with accept and dismiss workflows.
- Added category spending trend analysis using comparable 8-week periods.
- Added unusual-spending detection with baseline, current amount and percentage explanation.
- Added one-off baseline exclusion support.
- Added merchant summary/detail foundations for future Insights.

### Changed
- Updated version references to v0.10.0.
- Added a source-independent intelligence pipeline for manual transactions, CSV imports and future CDR/Open Banking transactions.
- Kept detected recurring items out of committed forecasts until accepted by the user.

### Security and privacy
- Spending Intelligence operates locally on the user's own Fynvo data.
- No transaction history is sent to external AI or analytics services.
- Regex rules are validated before use.

### Deferred
- Broader financial-health insights remain planned for v0.14.0.
- Australian Open Banking/CDR remains planned for v0.12.0.

## v0.9.0

### Added
- Added end-to-end editing entry points for Accounts, Transactions, Categories, Bills, Recurring Expenses, Income, Planned Spending and Budgets.
- Added reusable edit modals that load existing values, save to update APIs and persist after page refresh.
- Added effective-dated edit support for income, recurring expenses and budgets so future changes can be tracked separately from corrections.
- Added edit history records for important financial record changes.
- Added CSV bank transaction import for Australian bank exports.
- Added column mapping for date, description, merchant, debit, credit and signed amount formats.
- Added support for DD/MM/YYYY, DD/MM/YY and YYYY-MM-DD dates.
- Added import preview with validation, invalid row reporting, duplicate detection and matching suggestions.
- Added import batches, import history and a reconciliation review queue.
- Added matching suggestions for Bills, Recurring Expenses and Planned Spending using amount, date and merchant/category similarity.
- Added Actual vs Expected variance storage for reconciliation links.
- Added category suggestions and merchant/description normalisation foundations for v0.10.0 Spending Intelligence.

### Changed
- Updated version references to v0.9.0.
- Updated the main Fynvo UI so editing is discoverable from every major financial list.
- Imported CSV transactions become first-class Actual transactions that feed budget, forecast, cash-flow and future report calculations.

### Fixed
- Corrected the v0.8.0 gap where editing existing financial records was not available in the released UI.

### Security
- Import, edit and reconciliation APIs require the existing authenticated session and remain scoped to the authenticated user.
- CSV content is treated as untrusted text, constrained by size and never executed.

### Deferred
- Advanced rule learning, anomaly detection and recurring-payment discovery remain planned for v0.10.0 Spending Intelligence.
- Full Open Banking/CDR import remains planned for v0.12.0.

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

### Deferred
- Full visual drag-and-drop column configuration and report export remain future UI refinements.
- CSV import and reconciliation remain planned for v0.9.0.
- Full Home Assistant budget sensors remain planned for v0.15.0.
