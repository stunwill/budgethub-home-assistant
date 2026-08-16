# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v0.5.0

### Added
- Planned Spending management with Idea, Wishlist, Planned, Committed, Purchased and Cancelled statuses.
- Include in Forecast support so planned spending can be used for scenarios without deleting records.
- Enhanced Month view with Monday-Sunday weekly columns and clickable week/month totals.
- Planned Spending integration into Week, Month, Pay Cycle and Year views.
- Fynvo logo, mark and favicon assets.

### Changed
- Overview Planned Spending and Top Planned Spending now use real data.
- Annual matrix totals now include forecast-enabled planned spending when appropriate.

### Fixed
- Planned spending remains planned and does not create fake actual transactions.

### Security
- Planned Spending APIs require authentication and are scoped to the authenticated user.

## v0.4.0

### Added
- Income, Recurring Expenses, incomplete recurring tracking, Bills/Obligations, overdue tracking and Week/Month/Pay Cycle/Year financial views.
- Annual Jan-Dec matrix with drill-down cells.

## v0.3.0

### Added
- Accounts, Transactions, Transfers and real dashboard financial position.

## v0.2.0

### Added
- Fynvo foundation, authentication, SQLite persistence and responsive Overview dashboard.
