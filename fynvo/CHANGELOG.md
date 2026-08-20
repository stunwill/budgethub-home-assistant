# Fynvo Add-on Changelog

## v1.0.0 - Stable Production Release

### Production readiness
- First stable Fynvo release, focused on acceptance, upgrade safety, data preservation, security and supportability rather than major feature expansion.
- Added formal v1.0 acceptance documentation separating repository-verifiable checks from installed Home Assistant/manual release gates.
- Added documented backup/restore procedure for Fynvo persistent data under `/data`.
- Added explicit known limitations so deferred capabilities are not represented as delivered.

### Stable baseline
- Retains the v0.18.0 Category normalisation, merge, integrity, recurring duplicate-review, Card-integrity and commitment duplicate-suppression improvements.
- Retains authentication/bootstrap/recovery, Accounts, Cards, Transactions, Transfers, Income, Recurring Expenses, Bills, Planned Spending, Categories, Budgets, Forecasting, Financial Calendar, Scenarios, Goals, CSV import, reconciliation foundations, Spending Intelligence, Insights and responsive/mobile functionality.
- Retains the removal of the redundant Overview seven-day Upcoming card and the Income Date Range control.

### Versioning
- Version updated to 1.0.0 across the Home Assistant add-on, backend and frontend.

### Release gates
- Installed Home Assistant ingress, representative upgrade, iPhone/mobile acceptance and Home Assistant backup/restore must be recorded as manual release gates when they cannot be executed by automated repository tests.
- Fynvo v1.0.0 must not be represented as fully accepted until required manual gates are actually completed.

### Deferred
- Direct ING connectivity and a new production CDR/Open Banking provider.
- Automatic production bank sync and production-grade automatic reconciliation.
- Advanced household roles/permissions, immutable audit logs and complete user activity/change history.
- Home Assistant financial entities and standalone Cloudways deployment.

## v0.18.0 - Financial Data Integrity, Category Management & Workflow Polish

### Added
- Category merge preview and confirmation workflow that reassigns linked financial records and deactivates the source Category without deleting history.
- Category health checking for duplicate parents/children, orphan relationships, circular hierarchy, invalid/inactive references, stale Category paths and Category-type conflicts.
- Non-destructive recurring-expense duplicate review using normalised names, amount, cadence, payment source and due-date proximity.
- Card integrity diagnostics for orphan Cards and active Cards attached to archived Accounts.
- Upcoming Commitments service foundation with overdue inclusion and duplicate suppression.
- CI-equivalent local validation script for compile, Ruff, backend tests, frontend tests/build, metadata and Docker checks.

### Changed
- Category create and edit now treat case differences and repeated/leading/trailing whitespace as the same Category name within a parent.
- Parent merges safely consolidate duplicate child Categories while preserving linked values and history.
- Category management is more compact on mobile and no longer over-emphasises repeated `0 entries` links.
- Recurring Expenses surface possible duplicate groups for review without automatically merging them.
- Mobile financial record spacing is tightened while preserving touch targets.
- Version updated to 0.18.0 across the Home Assistant add-on, backend and frontend.

### Preserved
- Upcoming Commitments remains the authoritative outgoing-obligation list. The redundant seven-day Upcoming Overview card remains removed.
- Income remains independent of the global Date Range selector.
- Linked Bill/Recurring Expense schedule suppression and effective-dated recurring amount changes continue to preserve existing forecast behaviour.
- No direct ING integration, new production CDR provider, bank credentials or standalone Cloudways deployment is introduced in this release.

### Regression protection
- Category duplicate create/update coverage including case and whitespace normalisation.
- Category merge and linked-record preservation coverage.
- Category health duplicate-detection coverage.
- Non-destructive recurring duplicate review coverage.
- Commitment duplicate-suppression unit coverage.

## v0.17.0 - Core Reliability & Pre-v1.0 Hardening

### Fixed
- Fixed Account creation from Accounts > Add. The generic modal previously sent new Accounts to `PUT /api/accounts/null`, causing the literal `null` path segment to be parsed as integer `account_id`.
- Fixed the shared RecordTable create path so new records use `POST` create endpoints and existing records use ID-based `PUT` updates.
- Fixed transfers into liability accounts so a credit-card/loan payment reduces the amount owing.
- Reinforced the mobile navigation drawer so it remains off-canvas and closed by default at phone widths.
- Fixed Australian date-only display handling to avoid UTC-driven one-day shifts.

### Changed
- Added user-friendly Account Type labels and expanded stable account identifiers for Offset, Car Loan, Line of Credit, Investment and Superannuation while preserving legacy `vehicle_loan` compatibility.
- Added explicit asset/liability classification to Account responses.
- Available Cash now includes active Transaction, Savings, Offset and Cash accounts only.
- Liability opening balances are entered as positive amounts owing.
- Archived Accounts remain available historically but are excluded from active selectors and blocked from new manual transactions/transfers.
- Improved user-facing validation messages and compact mobile Account/page actions.
- Version updated to 0.17.0 across Home Assistant add-on, backend and frontend metadata.

### Regression protection
- Exact `Kristy - Main AC` create/edit regression coverage.
- Account balance and cent-precision regression coverage.
- Available Cash and liability transfer coverage.
- Archived-account write protection coverage.
- Frontend create-versus-update contract and mobile navigation regression coverage.
- v0.15 authentication/recovery/session tests retained.

### Pre-v1.0
- Added a v1.0 readiness report. Installed Home Assistant ingress acceptance, representative v0.16.0 upgrade testing and backup/restore validation remain release gates before stable v1.0.0.
- The actual merged repository does not contain the previously proposed Home Assistant financial sensors/entities, so this release does not claim them as delivered.
