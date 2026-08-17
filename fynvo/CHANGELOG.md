# Fynvo Add-on Changelog

## v0.12.0

### Added
- Home Assistant administrator bootstrap options for first-run access.
- Secure idempotent initial administrator creation.
- Administrator recovery mode.
- Provider-neutral Bank Connections foundation for Australian Open Banking / CDR readiness.
- Mock Australian bank provider for development and testing.
- Bank connection, external account, transaction identity and sync-history storage.
- Connected account discovery, linking and balance sync metadata.
- Bank transaction sync into the existing transaction pipeline.
- Pending-to-posted and duplicate-prevention foundations.
- Reconciliation suggestions for synced bank transactions.
- Fynvo favicon asset.

### Changed
- Version updated to 0.12.0.
- Upcoming now means the next seven-day financial agenda and may include income.
- Upcoming Commitments now means outgoing obligations over the selected dashboard horizon.
- Overdue items are separated from future Upcoming events.
- Bank sync and CSV import coexist in the same Actual transaction model.

### Fixed
- Fresh installs no longer leave the owner guessing how to create the first administrator.
- Past unresolved records no longer appear as future Upcoming events.
- Dashboard outgoing amounts now display as negative obligations.

## v0.11.0

### Added
- First-class Financial Goals.
- Goal creation, editing, completion and cancellation.
- Goal progress, required contribution and forecast completion calculations.
- Weekly, true fortnightly and monthly contribution support.
- Goal account allocations and unallocated savings reporting.
- Goal contribution tracking.
- Goal What-If contribution calculations.
- Goal and Planned Spending link foundation.
- Redesigned Overview dashboard aligned to the Fynvo dashboard mock-up.
- Dashboard KPI row, Cash Flow Forecast chart, Forecast Summary, Upcoming Commitments, Quick Stats, Budget Overview and Goals summary.

### Changed
- Version updated to 0.11.0.
- The Overview dashboard now prioritises household financial information instead of development-status cards.
- Quick Add has clearer type-specific forms and validation messages.

## v0.10.0

### Added
- Spending Intelligence review queue.
- Merchant/payee normalisation.
- Merchant and categorisation rules.
- Category suggestions with confidence and evidence.
- Recurring expense and income detection.
- Recurring amount-change detection.
- Spending trends and unusual-spending detection.
- One-off baseline exclusion support.

### Changed
- Version updated to 0.10.0.
- Spending intelligence is local, deterministic and user-controlled.

## v0.9.0

### Added
- Editing for existing Accounts, Transactions, Categories, Bills, Recurring Expenses, Income, Planned Spending and Budgets.
- CSV bank transaction import with Australian date support.
- Column mapping, import preview, duplicate detection and validation.
- Reconciliation review queue for matching imported Actuals to Bills, Recurring Expenses and Planned Spending.
- Import history and import-batch tracking.

### Changed
- Version updated to 0.9.0.
- Financial list screens now expose clear Edit actions.

### Fixed
- Completed the missing v0.8.0 record-editing requirement.
