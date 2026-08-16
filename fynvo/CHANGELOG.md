# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

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
- Added account management for transaction, savings, credit-card, cash, loan, mortgage, asset and liability accounts.
- Added calculated account balances using opening balance plus ledger transactions.
- Added manual income and expense transactions.
- Added account-to-account transfers that link both ledger sides and do not count as income or expenditure.
- Added transaction search/filter foundations by account, date range, type and text.
- Added running balance support for account detail views.
- Added dashboard financial-position data from real accounts and transactions.
- Added transaction metadata fields for future CSV import, reconciliation and recurring-cost discovery.
- Added mandatory release changelog/release-note process documentation for all future releases.

### Changed
- Updated Fynvo version references to v0.3.0.
- Updated the Overview dashboard to use real available cash, assets, liabilities, net position, account count and recent transaction data where available.
- Updated the roadmap to mark v0.2.0 completed and record v0.3.0 delivered scope.

### Fixed
- Fixed the root application route so `/` deterministically returns the Fynvo application response instead of intermittently returning HTTP 404 when frontend assets are unavailable.
- Fixed frontend asset handling for Home Assistant ingress by using a relative Vite base path.
- Added SPA fallback support for implemented and future frontend routes without intercepting `/api/...` routes.

### Security
- Account and transaction APIs require the authenticated server-side session introduced in v0.2.0.
- Financial data is scoped to the authenticated user to preserve a clean path toward future household finance.

## v0.2.0

### Added
- Fynvo foundation, authentication, local SQLite persistence and responsive Overview dashboard.
- First-run administrator setup, username/password login, server-side sessions, logout and password change.
- Initial architecture, authentication and installation documentation.
