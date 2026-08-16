# Fynvo Product Roadmap

This roadmap is the canonical development queue for Fynvo. Future development should update this file rather than creating parallel release plans.

## Product principles

1. Forecast actual dated cash flow, not just monthly averages.
2. Keep financial data local by default.
3. Separate budgeted, planned and actual financial activity.
4. Make scenario planning simple enough for everyday household use.
5. Keep the financial domain independent from Home Assistant deployment concerns.
6. Prefer clear, auditable calculations over opaque automation.
7. Support Australian household finance first while avoiding unnecessary blockers to later internationalisation.

## Core product concepts

### Budget
A budget is how much the user intends or allows themselves to spend for a category, account, household member, period or goal.

### Planned
Planned is what the user currently expects or intends to spend or receive. Planned entries include known future purchases, forecast income and known recurring commitments.

### Actual
Actual is what really occurred based on recorded, imported or reconciled transactions. Transactions created in v0.3.0 are actual financial activity, not planned or budget records.

## Release definition of done from v0.3.0 onward

Every release must include a version bump, database migrations where required, automated tests, CI validation, a CHANGELOG entry, Home Assistant release notes, a Git tag, a GitHub Release and user-readable release notes.

Home Assistant application access is a release blocker. Fynvo must open through Home Assistant ingress, `/` must not intermittently return 404, login must work through ingress, protected APIs must remain protected and the add-on must not enter an unexplained restart loop.

## Release plan

### v0.2.0 - Fynvo Foundation + Dashboard

Status: Completed.

Delivered scope:
- complete Fynvo rebrand;
- Home Assistant add-on foundation;
- SQLite persistence under `/data`;
- first-run administrator setup;
- username/password login;
- secure password hashing;
- server-side session enforcement;
- responsive application shell;
- Overview dashboard with real-data empty states.

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
- priority and paid-through date support;
- weekly, monthly, pay-cycle and annual schedule views;
- Excel-style Jan-Dec annual matrix with drill-down;
- initial household recurring-expense and outstanding-obligation datasets.

### v0.5.0 - Planned Spending & Enhanced Financial Views

Status: Implemented in the v0.5.0 development PR.

Product outcome: the Planned layer of Fynvo, plus clearer drill-down from annual totals to monthly, weekly and individual items.

Delivered scope:
- Planned Spending records;
- statuses: Idea, Wishlist, Planned, Committed, Purchased and Cancelled;
- priority support;
- forecast inclusion/exclusion;
- incomplete planned-spending records;
- planned spending integration with Overview, Week, Month, Pay Cycle and Year views;
- enhanced Month view broken into Monday-Sunday weekly columns;
- weekly totals and monthly totals;
- clickable weekly, monthly and annual totals;
- annual matrix support for forecast-enabled Planned Spending;
- canonical Fynvo logo, mark and favicon assets;
- documentation for Planned Spending, matrix drill-down and branding assets.

### v0.6.0 - Cash Flow Forecasting

Product outcome: forecast future financial position.

Planned scope:
- dated forecast engine;
- combine current balances, income, recurring expenses, bills and planned spending;
- 30/60/90 day and custom ranges;
- projected balance chart;
- low-balance warnings;
- explainable forecast entries.

### v0.7.0 - Calendar & Categories
Financial calendar, reusable categories, tags and category-level dashboard summaries.

### v0.8.0 - Budgeting
Category budgets by month/pay cycle and budgeted vs planned vs actual comparisons.

### v0.9.0 - CSV Import & Reconciliation
Bank CSV uploads, mapping, duplicate detection, imported transaction review and matching against expected income, recurring expenses, planned purchases and actual transactions.

### v0.10.0 - Recurring Cost Discovery
Analyse imported transaction history to identify recurring expenses missing from Fynvo.

### v0.11.0 - Reports & Analytics
Trends, comparisons and financial reporting.

### v0.12.0 - Goals & Savings
Savings targets and contribution planning.

### v0.13.0 - Debt Planner
Loans, mortgages and debt strategies.

### v0.14.0 - Household Finance
Multi-user and shared/private finances.

### v0.15.0 - Home Assistant Integration
Sensors, services, dashboards and automations.

### v0.16.0 - Financial Intelligence
Contextual financial insights.

### v0.17.0 - Scenario Planning
What-if financial modelling.

### v0.18.0+ - Connected Banking
Australian Open Banking/CDR and automated feeds.

## CSV import and recurring-cost discovery requirements

CSV bank transaction imports will eventually be used to:

- compare planned versus actual spending;
- match imported transactions against expected income, recurring expenses and planned purchases;
- detect duplicate imports;
- identify transactions that cannot be matched;
- detect likely recurring expenses that have not been entered into Fynvo;
- recommend creation of new recurring expenses based on transaction history.

The v0.3.0 transaction schema preserves source, raw description, external identifier, import batch, import date, reconciliation state, amount, date, account, category and merchant fields to support these future workflows. The v0.4.0 scheduled-finance schema adds providers, aliases, expected dates, recurrence frequency, account/source account text and categories. The v0.5.0 Planned Spending schema adds amount, approximate date, merchant/provider, category, account, status and forecast inclusion so planned purchases can later be reconciled against actual imported bank transactions.
