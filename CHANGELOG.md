# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v1.0.0 - Stable Production Release

### Production readiness
- Established v1.0.0 as Fynvo's first stable-production baseline, focused on acceptance, data preservation, security, upgrade safety and supportability rather than major feature expansion.
- Added a formal v1.0 acceptance checklist separating repository-verifiable gates from installed Home Assistant/manual release gates.
- Added documented Home Assistant backup and restore procedures for Fynvo's persistent `/data` state.
- Added explicit v1.0 known limitations so deferred capabilities are not represented as delivered.
- Added v1.0 release notes describing required automated and manual acceptance evidence.

### Versioning
- Updated Home Assistant add-on, backend and frontend release metadata to 1.0.0.
- Retained historical v0.x documentation and version references where they describe earlier releases.

### Stable baseline
- Retained v0.18.0 Category normalisation, merge, integrity diagnostics, recurring duplicate review, Card integrity diagnostics and Upcoming Commitments duplicate-suppression foundations.
- Retained the corrective removal of the redundant Overview `Upcoming / Next 7 days` card and the Income Date Range control.
- Retained existing authentication/bootstrap/recovery, Accounts, Transactions, Transfers, Income, Recurring Expenses, Bills, Planned Spending, Budgets, Goals, Forecasting, CSV import, reconciliation foundations, Spending Intelligence, Insights and responsive/mobile functionality as the v1.0 acceptance surface.

### Release gates
- Installed Home Assistant ingress, representative upgrade, iPhone/mobile acceptance and Home Assistant backup/restore remain manual release gates when they cannot be executed in the development environment.
- v1.0.0 must not be tagged as fully accepted based solely on source-level tests if those manual gates remain unverified.

### Deferred
- Direct ING connectivity and new production Open Banking/CDR provider integration.
- Automatic production bank synchronisation and production-grade automatic reconciliation.
- Advanced multi-user household roles and permissions, immutable audit logs and complete user activity/change history.
- Home Assistant financial sensors/entities and standalone Cloudways deployment.

## v0.18.0 - Financial Data Integrity, Category Management & Workflow Polish

### Added
- Added a supported Category merge workflow with a preview of affected Transactions, Income, Recurring Expenses, Bills, Planned Spending, Budgets and child Categories before any changes are made.
- Added Category health diagnostics for duplicate parent/child Categories, orphan children, children of inactive parents, circular relationships, orphan/inactive references, stale denormalised paths and Category-type conflicts.
- Added recurring-expense duplicate review using normalised name, amount, frequency, payment source and due-date proximity. Possible duplicates are surfaced for review and are never merged automatically.
- Added Account/Card integrity diagnostics for orphan Cards and active Cards linked to archived Accounts.
- Added a filtered Upcoming Commitments service foundation with overdue inclusion and duplicate-suppression support.
- Added a single-command CI-equivalent validation script covering Python compilation, Ruff, backend tests, application import, frontend tests/build, Home Assistant metadata and Docker build.

### Changed
- Category duplicate prevention now normalises case, leading/trailing whitespace and repeated whitespace for create and rename/move operations.
- Category merges preserve financial history by reassigning references and deactivating the source Category rather than deleting it.
- Merging parent Categories also consolidates same-name child Categories under the destination while retaining their linked records.
- Categories mobile presentation is more compact and no longer gives zero-entry links unnecessary visual emphasis.
- Categories now expose `Check Category Data` and `Merge Category` actions directly from the management page.
- Recurring Expenses now surface possible duplicate groups without automatically changing household data.
- Mobile financial table/card spacing has been tightened while preserving touch targets and desktop behaviour.
- Version metadata is aligned to v0.18.0 across the backend, frontend and Home Assistant add-on.

### Preserved behaviour
- The redundant Overview `Upcoming / Next 7 days` card remains removed. `Upcoming Commitments` remains the authoritative future-obligation view.
- The Income page remains independent of the global Date Range selector.
- Existing linked Bill/Recurring Expense schedule suppression remains in place so a linked Bill and its generated recurring occurrence are not both scheduled for the same date.
- Effective-dated recurring amount changes remain the mechanism for changes such as `$140/month` becoming `$80/month` from a future date without rewriting history.
- No direct ING connectivity, new production Open Banking/CDR provider, bank credentials or Cloudways migration is introduced by this release.

### Regression protection
- Added tests for case/whitespace Category duplicate prevention on create and update.
- Added Category merge coverage proving linked Recurring Expense data survives parent/child consolidation.
- Added Category health coverage for historical duplicate detection.
- Added recurring-expense duplicate-review coverage proving detection is non-destructive.
- Added commitment duplicate-suppression unit coverage.

## v0.17.0 - Core Reliability & Pre-v1.0 Hardening

### Fixed
- Fixed the release-blocking Accounts `+ Add` workflow. New records were incorrectly sent to the update route as `PUT /api/accounts/null`, causing FastAPI to parse `null` as the integer `account_id` and return the reported raw validation error.
- Fixed the shared create/edit modal contract so new records use the entity create endpoint with `POST`, while existing records continue to use the ID-based update endpoint with `PUT`.
- Fixed internal transfers involving liability accounts so payments to a credit card or loan reduce the amount owing instead of increasing it.
- Reinforced mobile drawer CSS so the application navigation remains off-canvas and closed by default at mobile widths.
- Adjusted Australian date-only rendering so financial dates are anchored to local midnight rather than accidentally shifting because of UTC parsing.

### Changed
- Added friendly Account Type labels for Transaction Account, Savings Account, Offset Account, Credit Card, Cash, Mortgage, Personal Loan, Car Loan, Line of Credit, Investment Account, Superannuation, Other Asset and Other Liability.
- Defined explicit asset/liability semantics. Liability opening balances are entered as positive amounts owing and Fynvo applies the internal balance rules.
- Available Cash now intentionally includes only active Transaction, Savings, Offset and Cash balances. Investments, Superannuation, non-liquid assets and liabilities are excluded from Available Cash.
- Archived accounts remain available for historical retrieval but are excluded from normal active account lists and cannot receive new manual transactions or transfers.
- Normal validation failures are translated into concise user-facing messages instead of exposing raw Pydantic integer/field errors in the main workflow.
- Mobile page actions and Account forms/modals are more compact and touch-friendly.
- Updated release metadata to v0.17.0 across the Home Assistant add-on, backend and frontend.

### Regression protection
- Added the exact `Kristy - Main AC` account creation regression with a $2,000.00 opening balance, ING institution and generated Account ID.
- Added same-ID Account edit/no-duplicate coverage.
- Added Account balance, liability payment transfer, Available Cash, account-type metadata and archived-account write-protection tests.
- Expanded frontend regression tests for create-versus-update routing, user-friendly Account types, validation messaging and reinforced mobile navigation behaviour.
- Retained the v0.15 authentication/bootstrap/recovery/session regression suite and the v0.16 responsive navigation architecture.

### Pre-v1.0 status
- Added `docs/V1_READINESS_v0.17.0.md` with BLOCKER, HIGH, MEDIUM and LOW readiness gaps.
- Real Home Assistant ingress testing, representative v0.16.0 upgrade validation and backup/restore validation remain required before Fynvo should be tagged v1.0.0.
- The merged repository still does not contain the previously proposed Home Assistant financial sensor/entity implementation, so v0.17.0 does not claim those entities as delivered.
