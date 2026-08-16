# Changelog

All notable Fynvo changes will be documented here.

## [0.2.0] - 2026-08-16

### Added
- Combined Fynvo foundation and dashboard release.
- First-run administrator setup.
- Username/password authentication with salted PBKDF2 password hashing.
- Server-side session storage with HttpOnly session cookies and expiry.
- Login, logout, current-user and password-change API endpoints.
- Protected dashboard API endpoint.
- Basic login brute-force protection.
- SQLite schema migration foundation stored under persistent `/data`.
- Responsive Fynvo application shell and Overview dashboard.
- Reusable frontend components for navigation, summary cards, empty states, buttons and form fields.
- Canonical Fynvo roadmap through v0.18.0+.
- Backend tests for authentication, session behaviour, dashboard protection, password hashing and migration state.

### Changed
- Updated app/add-on version to `0.2.0`.
- Docker build now builds the React frontend and serves it from FastAPI.
- CI now runs backend tests in addition to linting, frontend build and add-on Docker build.

### Security
- Financial dashboard data and protected API endpoints now require authentication.
- Passwords are never stored in plaintext and hashes are not exposed by API responses.

### Known limitations
- v0.2.0 intentionally does not implement accounts, transactions, income scheduling, recurring expense scheduling, planned spending records or full cash-flow calculations.
