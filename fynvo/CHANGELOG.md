# Fynvo Add-on Changelog

## v0.16.0 - Mobile Experience & Responsive Navigation

### Added
- Hamburger-controlled mobile navigation using the existing Fynvo navigation as an off-canvas drawer.
- Dimmed backdrop dismissal, explicit close control and Escape-key dismissal.
- Background scroll locking while the mobile drawer is open, with independent drawer scrolling.
- Safe-area-aware iPhone drawer layout using dynamic viewport height with fallback.
- Mobile focus management, `aria-expanded`, `aria-controls`, navigation labelling and reduced-motion support.
- Responsive navigation regression tests covering required dismissal paths, breakpoints, safe areas and scroll locking.

### Changed
- Phone and narrow tablet layouts now show financial page content immediately instead of placing the complete navigation above it.
- Navigation becomes a single-column mobile drawer below the responsive breakpoint while desktop keeps the established persistent sidebar.
- Mobile forms use available width more effectively.
- Data-heavy tables retain their desktop information and become horizontally scrollable on narrow displays.
- Mobile modals respect dynamic viewport height, safe areas and internal scrolling.
- KPI cards and action layouts stack progressively for small phones, including 320px-wide displays.
- Version updated to 0.16.0 across Home Assistant add-on, backend and frontend metadata.

### Fixed
- Fixed the release-blocking mobile issue where the full navigation menu remained permanently expanded and occupied most of the visible iPhone screen.
- Fixed stale mobile drawer and scroll-lock state when moving between responsive breakpoints.
- Fixed mobile navigation remaining open after selecting a destination.

### Compatibility
- v0.15.0 authentication/bootstrap/recovery/session functionality is retained and continues to be covered by backend regression tests.
- Existing Fynvo financial pages, Insights, scenarios, budgeting, editing, CSV import and reconciliation code are not replaced by a separate mobile implementation.

### Manual acceptance
- A real Home Assistant ingress/iPhone acceptance run is still required before the v0.16.0 mobile release gate can be declared fully passed.

## v0.14.0

### Added
- First-class explainable Financial Insights with evidence, severity, lifecycle status and drill-down targets.
- Financial Health overview across Cash Flow, Budgets, Spending, Recurring Commitments, Income, Goals and Data Quality without an opaque overall score.
- Cash Flow Insights for projected shortfalls, low-balance periods and unusually concentrated upcoming commitments.
- Budget Insights for projected overspend, budget pace, positive tracking and unbudgeted categories.
- Rolling 8-week spending trend Insights that respect one-off baseline exclusions.
- Recurring commitment monthly and annual equivalent analysis.
- Income versus expected schedule analysis and a guarded savings-rate calculation when data quality is sufficient.
- Goal health Insights for ahead/behind status and competing contribution requirements.
- Scenario impact Insights using isolated baseline-versus-scenario comparisons.
- Data Quality Insights for uncategorised transactions, reconciliation backlog and stale connected-bank data.
- Insight dismissal, reviewed and resolved states with suppression of unchanged dismissed conditions.
- Responsive Insights page with Financial Health dimensions, filtering, explainable evidence and context actions.
- Overview Financial Health card showing only the highest-priority active Insights.

### Changed
- Version updated to 0.14.0 across Home Assistant add-on, backend and frontend metadata.
- Overview attention handling now uses the shared Insights and Financial Health service instead of only counting Spending Intelligence suggestions.
- Budget Overview now consumes the actual budget-analysis rows returned by the Budget service.
- Quick Stats now consistently labels average monthly net forecast.

### Security and privacy
- Insight generation runs locally against the household's existing Fynvo data.
- No household financial records are sent to an external AI or analytics service for v0.14.0 Insights.
- Insight wording remains factual and avoids unsupported personal financial recommendations.

### Deferred
- Home Assistant financial sensors, cards and automations remain scheduled for v0.15.0.
- Production CDR provider expansion, richer Reports, multi-user permissions, User Activity, Audit Logs and Record Change History remain production-readiness work before v1.0.

## v0.13.0

### Added
- Improved administrator credential adoption and recovery so Home Assistant-configured credentials map to the persisted Fynvo administrator account.
- Added expanded authentication regression coverage for configured credentials and recovery behaviour.
- Added persistent Scenario Intelligence service foundations using the existing forecast engine.
- Added Galano Grotesque Medium web typography for the approved Fynvo login and branding experience.

### Changed
- Version updated to 0.13.0 across Home Assistant add-on, backend and frontend metadata.
- Updated login/authentication styling foundations for the approved responsive Fynvo design direction.

### Fixed
- Fixed a release metadata issue that prevented Home Assistant from detecting v0.13.0 after the implementation PR was merged.
- Fixed administrator configuration behaviour where configured credentials could differ from the persisted authentication account.

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
