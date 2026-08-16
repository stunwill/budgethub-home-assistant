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

## Core product concepts

### Actual
Money that has already been received or spent through recorded, imported or reconciled transactions.

### Committed
Known obligations and income sources such as recurring expenses, bills and scheduled income.

### Planned
Known or intended future spending that has not yet occurred.

### Budget
The amount the household intends or permits itself to spend for a category, period, account, person or goal.

### Forecast
What Fynvo calculates is likely to happen based on balances, commitments, plans, budgets where available and historical behaviour where appropriate.

### Scenario
A temporary or saved what-if view of what would happen if circumstances changed.

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

Status: Implemented in the v0.9.0 development PR.

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

Planned scope:
- recurring-payment detection;
- merchant normalisation;
- categorisation rules;
- spending trends;
- anomaly detection;
- rule learning from accepted import/reconciliation decisions.

### v0.11.0 - Goals & Financial Planning

Planned scope:
- savings targets;
- sinking funds;
- target dates;
- required contributions;
- goal forecasting;
- planning for irregular costs such as registration, insurance, Christmas, school expenses, holidays and home maintenance.

### v0.12.0 - Australian Open Banking / CDR

Planned scope:
- Australian CDR/Open Banking account connections;
- secure consent handling;
- account and transaction ingestion through the same pipeline as manual entry and CSV import.

### v0.13.0 - Forecast & Scenario Intelligence

Planned scope:
- saved scenarios;
- forecast confidence;
- forecast accuracy tracking;
- explainable scenario comparisons.

### v0.14.0 - Insights & Financial Health

Planned scope:
- explainable household finance insights;
- financial-health scorecards;
- risk warnings;
- trend interpretation.

### v0.15.0 - Home Assistant Integration

Planned scope:
- Home Assistant sensors;
- dashboard cards;
- automations for shortfalls, upcoming bills and budget warnings.

### v1.0.0 - Production Release

Planned scope:
- production hardening;
- installation polish;
- migration reliability;
- user documentation;
- stable release packaging.
