# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

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
