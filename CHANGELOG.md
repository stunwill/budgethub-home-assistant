# Changelog

All notable Fynvo changes are documented here. Starting with v0.3.0, every release must include a user-readable changelog entry, Home Assistant-visible release notes and GitHub release notes.

## v0.13.0

### Added
- Added administrator credential adoption and recovery improvements so configured Home Assistant credentials map to the persisted Fynvo administrator account.
- Added expanded authentication regression tests for configured credentials, recovery and persistence behaviour.
- Added persistent Scenario Intelligence service foundations that reuse the existing forecast engine.
- Added Galano Grotesque Medium web typography foundations for the approved Fynvo login and branding experience.

### Changed
- Updated release metadata to v0.13.0 across the Home Assistant add-on, backend and frontend.
- Continued the responsive login/authentication redesign and branding foundations for the approved desktop, tablet and mobile direction.

### Fixed
- Fixed the release metadata/versioning omission that prevented Home Assistant from detecting v0.13.0 after the implementation PR was merged.
- Fixed the legacy single-administrator configuration mismatch where Home Assistant configuration could show credentials that did not match the persisted administrator account.

## v0.12.0

### Added
- Added Home Assistant add-on administrator bootstrap fields for first-run access.
- Added idempotent initial administrator creation when no users exist.
- Added administrator recovery mode for controlled password recovery without deleting the database.
- Added provider-neutral Bank Connections architecture for Australian Open Banking / Consumer Data Right readiness.
- Added a mock Australian bank provider for development, demos and automated testing.
- Added Bank Connection records with provider, institution, status, consent state, last sync, consent expiry and error state.
- Added External Account mapping so provider account IDs are linked to Fynvo Accounts without becoming Fynvo primary IDs.
- Added account discovery, connected account creation/linking and ignore-account support.
- Added synchronised connected-account balances and balance freshness metadata.
- Added bank transaction ingestion into the existing Fynvo transaction table with source `bank_sync`.
- Added provider transaction identity tracking for idempotent sync and pending-to-posted matching.
- Added sync history with added, updated and duplicate/ignored counts.
- Added bank disconnect support that stops future sync without deleting historical transactions.
- Added reconciliation suggestions from bank transactions to Bills, Income and Planned Spending.
- Added browser favicon asset aligned to Fynvo branding.

### Changed
- Updated all release metadata to v0.12.0.
- Updated Home Assistant add-on configuration and schema for administrator bootstrap and session length.
- Corrected the Overview definitions for Upcoming, Upcoming Commitments and Overdue.
- Upcoming is now the next seven-day financial agenda and may include Income, Bills, Recurring Expenses and Planned Spending.
- Upcoming Commitments now follows the selected dashboard horizon and excludes ordinary Income.
- Overdue unresolved bills are separated from future Upcoming items.
- Dashboard event amounts now preserve direction: income is positive, outgoing obligations are negative.
- Quick Stats now labels average monthly commitments, planned spending and net forecast more clearly.
- Bank sync data now feeds the same Actual transaction pipeline used by Manual Entry and CSV Import.

### Fixed
- Fixed the release-blocking issue where a fresh Home Assistant installation could show a login page without a documented administrator bootstrap path.
- Fixed Upcoming date filtering so past unresolved records do not appear as future Upcoming events.
- Fixed Upcoming Commitments empty states caused by incorrect filtering.
- Fixed expense direction formatting in short-term dashboard agenda rows.

### Security and privacy
- No permanent default administrator password is committed.
- Administrator passwords are hashed before storage.
- Bootstrap configuration is ignored after an administrator exists unless explicit recovery mode is enabled.
- Bank provider credentials are not stored by v0.12.0.
- Mock bank data is clearly labelled as mock/development data.
- Sensitive provider payloads and tokens are not exposed to the frontend.

### Deferred
- Production CDR provider credentials, consent infrastructure and accredited-provider integration remain future work.
- Full User Management, User Activity, immutable Audit Logs and Record Change History are now explicit roadmap items before or as part of v1.0 readiness.

## v0.11.0

### Added
- Added first-class Financial Goals for savings, target balances, planned purchases, annual goals and debt-reduction targets.
- Added Goal creation, editing, completion and cancellation APIs.
- Added Goal progress with target, current, remaining, percentage complete, required contribution, current contribution and forecast completion date.
- Added weekly, true fortnightly and monthly contribution calculations.
- Added account allocations so one savings balance is not double-counted across multiple Goals.
- Added manual Goal contribution tracking.
- Added unallocated savings reporting by account.
- Added Goal to Planned Spending link foundation.
- Added Goal What-If contribution calculation with temporary forecast impact.
- Added a command-centre dashboard API for KPI cards, forecast summary, commitments, planned spending, budget snippets, goals and intelligence attention counts.
- Added a first-class Goals navigation destination and responsive Goals UI.

### Changed
- Redesigned the Overview dashboard to more closely match the supplied Fynvo dashboard mock-up.
- Replaced development-oriented Overview panels with household financial information.
- Added the five-card dashboard KPI row: Available Cash, Expected Income, Scheduled Commitments, Planned Spending and Projected Balance.
- Added a Cash Flow Forecast chart and Forecast Summary card to the Overview.
- Added Upcoming Commitments, Upcoming events, Top Planned Spending, Quick Stats, Budget Overview, Goals and Spending Intelligence attention cards.
- Improved Quick Add with type-specific forms and clearer backend validation errors.
- Updated version references to v0.11.0.

### Fixed
- Removed generic dashboard pending states where the data is simply empty.
- Reduced excessive unused Overview whitespace by using a denser responsive card layout.

### Deferred
- Full Scenario Intelligence remains planned for v0.13.0.
- Broader financial-health Insights remain planned for v0.14.0.
- Home Assistant entities for Goals remain planned for v0.15.0.

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
