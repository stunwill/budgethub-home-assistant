# Fynvo Product Roadmap

This roadmap is the canonical development queue for Fynvo. Future development should update this file rather than creating parallel release plans.

## Product principles

1. Forecast actual dated cash flow, not just monthly averages.
2. Keep financial data local by default.
3. Separate budgeted, planned, actual and forecast financial activity.
4. Make scenario planning simple enough for everyday household use.
5. Keep financial calculations clear, auditable and explainable.
6. Support Australian household finance first while allowing later internationalisation.
7. Maintain a cohesive Fynvo visual and navigation system across future modules.
8. Make Budget, Actual, Committed, Planned, Forecast and Scenario explicit in budget analysis.
9. Make financial records maintainable after creation.
10. Feed Manual Entry, CSV Import and future CDR/Open Banking into one Actual transaction pipeline.
11. Keep spending intelligence local, explainable and user-controlled.
12. Treat Goals as forward-looking financial planning records distinct from Budgets and Planned Spending.
13. The Overview dashboard should be a household financial command centre, not a development-status page.
14. Authentication must always have a documented owner bootstrap and recovery path.
15. User activity, audit events and record change history must become explicit production-readiness capabilities before v1.0.
16. Financial Insights must be evidence-backed, consistent with source financial calculations and free from unsupported personal financial advice.
17. Fynvo must remain one responsive application across phone, tablet, desktop and Home Assistant ingress.

## Core product concepts

### Actual
Money that has already been received or spent through recorded, imported, synchronised or reconciled transactions.

### Committed
Known obligations and income sources such as recurring expenses, bills and scheduled income.

### Planned
Known or intended future spending that has not yet occurred.

### Budget
The amount the household intends or permits itself to spend for a category, period, account, person or goal.

### Goal
A desired future financial position or amount, such as a savings target, emergency fund, planned purchase, annual obligation or debt-reduction target.

### Forecast
What Fynvo calculates is likely to happen based on balances, commitments, plans, budgets where available and historical behaviour where appropriate.

### Scenario
A temporary or saved what-if view of what would happen if circumstances changed.

### Insight
An explainable signal derived from core Fynvo financial calculations. An Insight describes what changed or matters, its comparison basis, supporting evidence and a route to inspect the underlying records. Insights are not the source of financial truth.

### Audit Event
An append-only record of what action occurred, when it occurred and which user/interface caused it.

### Change History
A versioned view of what data changed on a financial record, such as amount, date, category or status.

## Release definition of done from v0.3.0 onward

Every release must include a version bump, database migrations where required, automated tests, CI validation, a CHANGELOG entry, Home Assistant release notes, GitHub release notes and user-readable release notes.

Home Assistant ingress access, login, protected APIs and record-edit persistence are release blockers.

## Release plan

### v0.2.0 - Fynvo Foundation + Dashboard

Status: Completed.

Delivered scope:
- Home Assistant add-on foundation;
- SQLite persistence under `/data`;
- first-run administrator setup;
- username/password login;
- server-side session enforcement;
- responsive application shell.

### v0.3.0 - Accounts & Transactions

Status: Completed.

Delivered scope:
- account management;
- actual transactions;
- account-to-account transfers;
- dashboard financial position;
- transaction metadata fields for future CSV import and matching;
- deterministic Home Assistant ingress/root-route behaviour.

### v0.4.0 - Income, Recurring Expenses & Bills

Status: Completed.

Delivered scope:
- income source management;
- recurring expense management;
- incomplete recurring records;
- bills and financial obligations;
- overdue and due-state tracking;
- weekly, monthly, pay-cycle and annual schedule views;
- Excel-style Jan-Dec annual matrix with drill-down.

### v0.5.0 - Planned Spending & Enhanced Financial Views

Status: Completed.

Delivered scope:
- Planned Spending records;
- statuses: Idea, Wishlist, Planned, Committed, Purchased and Cancelled;
- forecast inclusion/exclusion;
- planned spending integration with Overview, Week, Month, Pay Cycle and Year views;
- canonical Fynvo branding assets.

### v0.6.0 - Cash Flow Forecasting & Financial Scenarios

Status: Completed.

Delivered scope:
- reusable cash-flow forecast engine;
- baseline and expected forecasts;
- projected balance timeline;
- lowest balance and shortfall detection;
- effective-dated amount changes;
- scenario comparisons without mutating real records.

### v0.7.0 - Financial Calendar & Category Management

Status: Completed.

Delivered scope:
- redesigned Fynvo interface;
- unified Financial Calendar;
- Cash Flow view;
- Quick Add;
- category visibility foundation.

### v0.8.0 - Advanced Budgeting

Status: Completed.

Delivered scope:
- first-class Budget domain model;
- expense budgets and income budget/target foundations;
- weekly, true fortnightly, monthly, quarterly and annual periods;
- annual allocation strategies;
- base budget, rollover and effective available budget separated;
- category hierarchy foundation;
- Independent, Shared Parent Pool and Parent Equals Sum of Children budget modes;
- Budget vs Actual vs Committed vs Planned vs Forecast analysis foundation;
- unbudgeted category detection;
- Saved Views / View Preferences foundation.

Deferred from v0.8.0 and corrected in v0.9.0:
- full edit UI for existing major financial records.

### v0.9.0 - Editing, CSV Import & Reconciliation

Status: Completed.

Delivered scope:
- full record editing for Accounts, Transactions, Categories, Bills, Recurring Expenses, Income, Planned Spending and Budgets;
- edit forms discoverable from the current screens;
- persistence after reload through update APIs;
- effective-dated edit support for income, recurring expenses and budgets;
- edit-history audit foundation;
- CSV bank transaction import;
- account selection during import;
- column mapping;
- Australian date support: DD/MM/YYYY, DD/MM/YY and YYYY-MM-DD;
- import preview;
- invalid-row reporting;
- duplicate detection;
- duplicate skipping by default;
- matching suggestions against Bills, Recurring Expenses and Planned Spending;
- Actual vs Expected variance for reconciliation links;
- import batches and import history;
- reconciliation review queue;
- category suggestion foundation;
- merchant/description normalisation foundation;
- imported transactions feeding Budgeting, Cash Flow, Forecasting and future Reports.

### v0.10.0 - Spending Intelligence

Status: Completed.

Delivered scope:
- reusable source-independent spending intelligence service;
- merchant/payee normalisation while preserving original descriptions;
- user-managed merchant rules;
- user-managed categorisation rules;
- rule preview and safe historical rule application;
- category suggestions with confidence and evidence;
- Spending Intelligence review queue;
- recurring expense detection;
- recurring income detection;
- recurring amount-change detection for increases and decreases;
- accepted recurring detections create confirmed recurring records;
- accepted amount changes use effective-dated change records where a matching record exists;
- category spending trend analysis;
- unusual-spending detection;
- one-off baseline exclusion;
- merchant summary foundations;
- local deterministic privacy-preserving analysis for future CDR/Open Banking, Goals, Scenarios and Insights.

### v0.11.0 - Goals & Financial Planning

Status: Completed.

Delivered scope:
- first-class Financial Goals domain;
- savings, target-balance, planned-purchase, annual and debt-reduction goal types;
- Goal creation, editing, completion and cancellation;
- Goal progress with target, current, remaining and percentage complete;
- weekly, true fortnightly and monthly required-contribution calculations;
- calculated on-track, ahead and behind status;
- forecast completion date from current contribution rate;
- account allocations and unallocated savings reporting;
- contribution tracking foundation;
- Goal and Planned Spending link foundation;
- Goal What-If contribution calculations using temporary forecast scenario impact;
- command-centre dashboard aggregation endpoint;
- redesigned Overview dashboard aligned to the supplied Fynvo mock-up;
- five-card KPI row;
- Cash Flow Forecast chart;
- Forecast Summary;
- Upcoming Commitments;
- Upcoming events;
- Top Planned Spending with Quick Add;
- Quick Stats;
- Budget Overview;
- Goals dashboard section;
- Spending Intelligence attention indicator;
- removal of development-oriented panels from the household Overview;
- improved Quick Add forms and validation feedback.

### v0.12.0 - Australian Open Banking / CDR Foundation, Admin Bootstrap & Branding

Status: Completed.

Delivered scope:
- Home Assistant add-on administrator bootstrap configuration;
- idempotent initial administrator creation when no users exist;
- explicit administrator recovery mode;
- password hashing and no permanent default credentials;
- first-run messaging for missing administrator configuration;
- provider-neutral Bank Connection architecture;
- mock Australian CDR provider for development and testing;
- institution discovery;
- external account discovery;
- external account to Fynvo account linking;
- connected-account balance metadata;
- bank transaction ingestion through the existing Actual transaction table;
- provider transaction identity tracking;
- pending-to-posted matching foundation;
- idempotent repeated sync;
- sync history;
- disconnect without deleting historical transactions;
- merchant normalisation handoff;
- reconciliation-link suggestions for Bills, Income and Planned Spending;
- expected vs actual variance preservation;
- Overview definitions corrected for Upcoming, Upcoming Commitments and Overdue;
- Upcoming is the next seven-day financial agenda and can include income;
- Upcoming Commitments uses the selected dashboard horizon and excludes ordinary income;
- overdue unresolved items remain visible but separate from future Upcoming;
- browser favicon and app metadata aligned to Fynvo branding.

Production CDR connectivity remains future work. v0.12.0 deliberately does not fabricate live bank connectivity without provider credentials, consent infrastructure or an appropriate Australian CDR intermediary.

### v0.13.0 - Authentication, Login UX, Branding Reliability & Scenario Foundations

Status: Completed.

Delivered scope confirmed from the merged repository:
- administrator credential adoption and recovery improvements so Home Assistant-configured credentials map to the persisted administrator account;
- persistent authentication regression coverage across setup, restart, login and password changes;
- responsive Fynvo login/authentication design foundations;
- official Fynvo branding and bundled Galano Grotesque Medium typography foundations;
- persistent Scenario records and Scenario adjustments;
- isolated baseline-versus-scenario comparisons using the shared forecast engine;
- effective-dated recurring-income and recurring-expense Scenario changes without mutating baseline records;
- one-off Scenario income/expense changes;
- Scenario created_by_user_id and updated_by_user_id metadata foundations;
- release metadata corrected so Home Assistant can detect the v0.13.0 update.

Forecast confidence calibration and long-term forecast-accuracy tracking remain future refinement areas rather than fabricated v0.13.0 functionality.

### v0.14.0 - Insights & Financial Health

Status: Completed.

Delivered scope:
- first-class Insights projection/lifecycle model with New, Reviewed, Dismissed and Resolved states;
- deterministic Insight fingerprinting so unchanged dismissed conditions do not immediately reappear;
- stale Insight resolution when the underlying condition no longer exists;
- retained supporting evidence, source references, time period, confidence where appropriate and drill-down targets;
- transparent Financial Health component summary with no opaque magic score;
- Cash Flow health for projected shortfalls and low-balance periods;
- upcoming financial-pressure detection based on scheduled commitments and an explicit comparison basis;
- Budget health using the existing Budget analysis service, including projected overspend, budget pace and meaningful positive tracking;
- unbudgeted-spending Insights;
- comparable rolling 8-week category-spending trends with one-off baseline exclusions respected;
- reuse of existing Spending Intelligence anomaly and recurring-change evidence rather than duplicate detection logic;
- recurring commitment monthly and annual equivalent analysis;
- Income versus scheduled-income analysis;
- guarded savings-rate calculation only when the underlying data is sufficiently complete;
- Goal ahead/behind Insights and combined Goal contribution pressure versus forecast surplus;
- active Scenario impact Insights using isolated baseline-versus-scenario comparisons;
- Data Quality Insights for uncategorised transactions, reconciliation backlog and stale connected-bank data;
- authenticated Insights APIs for list, detail, refresh, review and dismissal;
- responsive Insights interface with Financial Health dimensions, importance/category filters and expandable evidence;
- Overview Financial Health integration that prioritises a small number of high-value active Insights;
- local deterministic processing, with no external AI service receiving household transaction data.

### v0.15.0 - Authentication Reliability & Recovery Hardening

Status: Completed and merged.

Delivered scope confirmed from the merged repository:
- deterministic administrator authentication initialisation during FastAPI lifespan startup;
- authoritative authentication lifecycle/state handling;
- Home Assistant add-on option-source detection without logging secrets;
- fresh-install administrator bootstrap;
- explicit administrator recovery mode;
- in-place administrator recovery preserving the user primary key and financial ownership relationships;
- atomic recovery with rollback on failure;
- deterministic recovery target selection and safe ambiguity/collision handling;
- recovered-administrator session revocation;
- stale failed-login cleanup for the recovered identity;
- `session_days` consistency across browser cookie and database session expiry;
- minimal public authentication state and protected administrator diagnostics;
- authentication and legacy-database regression coverage;
- Home Assistant ingress authentication remains the deployment boundary.

The v0.15.0 release plan also proposed Home Assistant financial sensors/entities and automation actions. Those entities are not present in the actual merged repository and are therefore retained as future work rather than being marked delivered.

### v0.16.0 - Mobile Experience & Responsive UI

Status: Implemented in the v0.16.0 development branch, pending CI, real Home Assistant ingress mobile acceptance and PR merge.

Scope:
- Mobile Navigation Drawer;
- Responsive Application Shell;
- shared authoritative navigation configuration across breakpoints;
- hamburger-controlled navigation closed by default on mobile;
- backdrop and automatic dismissal after navigation;
- mobile scroll locking and independent drawer scrolling;
- iPhone safe-area and dynamic viewport handling;
- active-route and touch-target improvements;
- keyboard/Escape/focus accessibility improvements;
- Mobile Dashboard Optimisation;
- Mobile Tables;
- Mobile Forms;
- Responsive Modals;
- Tablet Layout Refinement;
- desktop navigation preservation;
- responsive regression testing across representative phone, tablet and desktop viewport categories.

Release gate: opening Fynvo through Home Assistant ingress on an iPhone-sized viewport must show financial page content immediately with the navigation closed. The drawer must open only from the hamburger control and close after route selection or backdrop dismissal.

### Future Home Assistant Financial Integration

Planned scope retained from the original v0.15.0 roadmap:
- Home Assistant financial sensors/entities;
- automation-friendly numeric financial state;
- dashboard cards;
- shortfall, upcoming bill, budget-risk, Insight and Goal automation foundations;
- sensor-friendly Financial Health component states;
- useful states such as available cash, forecast balance, lowest projected balance, overdue count, budget risk and Goal progress;
- Home Assistant notifications/actions that link back to Fynvo without duplicating core financial calculations;
- strict authentication/privacy boundary and no sensitive financial detail in entity attributes.

### Future production-readiness release - User Management, Activity, Audit Logs & Change History

Planned scope before or as part of v1.0 readiness:
- household user creation, editing, deactivation and reactivation;
- password reset and password recovery workflows;
- roles and permissions such as Administrator, Household Member and Read Only where appropriate;
- household membership;
- display names and profiles;
- last-login and account-status visibility;
- User Activity for login, logout, record creation, record editing, CSV import, bank connect/disconnect, budget changes, reconciliation decisions, rules, scenarios, goals and configuration changes;
- immutable append-only Audit Logs that record timestamp, user, action, entity type, entity ID, source/interface and important metadata;
- separate record Change History showing previous value, new value and effective dates;
- created_by_user_id and updated_by_user_id metadata on important entities where practical;
- per-user Insight review/dismissal state when household multi-user support is introduced.

Future example:

#### Recurring Expense: Internet

Created: 5 Jan 2026, 10:42 by Stu. Amount: `$140/month`.

Changed: 1 Oct 2026, 09:15 by Stu. Amount: `$140 → $80`. Effective: `1 Oct 2026`.

Audit event: Stu edited Telstra Internet.

Change history: amount changed from `$140` to `$80`.

### v1.0.0 - Production Release

Planned scope:
- production hardening;
- installation and onboarding polish;
- migration and upgrade reliability;
- database integrity checks and safe recovery tooling;
- backup and restore guidance/workflows;
- authentication and session security hardening;
- household User Management and permission readiness;
- User Activity, Audit Log and per-record Change History readiness;
- richer Reports and export-ready data services;
- privacy and data-retention controls;
- support diagnostics that avoid exposing sensitive financial data;
- production CDR/provider expansion and consent lifecycle integration;
- bank-sync reliability, retry/backoff and reconciliation improvements;
- performance validation on larger transaction histories;
- error handling and degraded-provider behaviour;
- stable release packaging and user documentation.
