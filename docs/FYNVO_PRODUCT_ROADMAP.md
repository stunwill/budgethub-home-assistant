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

## Long-term product direction

Fynvo should answer:

- Where did my money go?
- What have I committed to?
- What am I planning to spend?
- What am I allowed to spend?
- What is likely to happen?
- What happens if something changes?
- Where will my finances be next week, next month and at the end of the year?

This mix of historical tracking, commitments, planning, budgeting, scenarios and forecasting is the defining product direction.

## Competitive analysis themes

Reviews of PocketSmith, YNAB, Frollo, WeMoney, Buxfer and Moneysoft highlighted useful future capabilities:

- daily cash-flow forecasting, calendar views and scenario planning;
- target-based budgeting, goals and sinking funds;
- Australian Open Banking/CDR account aggregation;
- recurring bills, subscriptions and payment reminders;
- transaction categorisation rules and merchant normalisation;
- cash-flow, budget-vs-actual and net-worth reporting;
- forecast shortfall and low-balance warnings;
- category spending trends and forecast accuracy tracking.

Fynvo should learn from these capabilities while preserving its own model: Actual, Committed, Planned, Budget, Forecast and Scenario remain distinct.

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

Home Assistant ingress access, login and protected APIs are release blockers.

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
- incomplete planned-spending records;
- planned spending integration with Overview, Week, Month, Pay Cycle and Year views;
- enhanced Month view broken into Monday-Sunday weekly columns;
- clickable weekly, monthly and annual totals;
- canonical Fynvo branding assets.

### v0.6.0 - Cash Flow Forecasting & Financial Scenarios

Status: Completed.

Delivered scope:
- reusable cash-flow forecast engine;
- baseline forecast from current balances, income, recurring expenses, bills and Planned Spending;
- expected forecast with conservative historical run-rate estimates;
- projected balance timeline;
- lowest forecast balance;
- projected shortfall detection;
- effective-dated amount changes for recurring income and recurring expenses;
- forecast chart data;
- forecast drill-down API;
- lightweight what-if scenario comparisons without mutating real records;
- dashboard forecast summary;
- documentation for Actual, Committed, Planned, Budget and Forecast.

### v0.7.0 - Financial Calendar & Category Management

Status: Completed.

Delivered scope:
- modern Fynvo dashboard based on the approved visual mock-up;
- dark navy sidebar and grouped navigation;
- reusable design-system foundation for cards, badges, modals, tables, charts, calendar events, alerts and responsive layout;
- unified Financial Calendar with day, week and month views;
- calendar events generated from the v0.6.0 forecast engine so income, recurring expenses, bills, Planned Spending and effective-dated changes stay consistent with Cash Flow;
- financial event drill-down;
- Cash Flow view with forecast chart and chronological timeline;
- Quick Add entry point for common financial records;
- category visibility foundation across transactions, income, recurring expenses, bills and Planned Spending;
- future navigation locations for Budgeting, Reports, Insights and Scenarios without fake functionality.

### v0.8.0 - Advanced Budgeting

Status: Implemented in the v0.8.0 development PR.

Delivered scope:
- first-class Budget domain model;
- expense budgets and income budget/target foundations;
- weekly, true fortnightly, monthly, quarterly and annual periods;
- annual allocation strategies for weekly, fortnightly and monthly equivalents;
- base budget, rollover and effective available budget kept separate;
- category hierarchy foundation with safe parent/child re-parenting and cycle prevention;
- budget relationship modes: Independent, Shared Parent Pool and Parent Equals Sum of Children;
- Budget vs Actual vs Committed vs Planned vs Forecast analysis foundation;
- current remaining, projected remaining, projected variance, utilisation and period-progress metrics;
- native-period and normalised date-range analysis foundation;
- proportional flexible budget calculations for partial periods;
- discrete scheduled commitments preserved as dated items, not pro-rated;
- account/category filter architecture;
- unbudgeted category detection with historical average foundation;
- transaction/item count foundations for drill-down;
- Saved Views / View Preferences storage for columns, sorting, filters, account/category selections and future reports;
- Reset View support;
- reusable services for future reports/export.

Deferred from v0.8.0:
- CSV import and reconciliation;
- full report/export UI;
- full persistent drag-and-drop table configuration UI;
- Home Assistant budget sensors.

### v0.9.0 - CSV Import & Reconciliation

Planned scope:
- CSV transaction import;
- configurable column mapping;
- Australian date formats;
- duplicate detection;
- transaction matching and reconciliation;
- categorisation;
- Planned vs Actual reconciliation;
- recurring transaction detection;
- merchant/payee normalisation;
- import preview;
- rollback where practical;
- architecture that can later accept CDR/Open Banking data.

### v0.10.0 - Spending Intelligence

Planned scope:
- detect subscriptions, utilities, insurance, mortgage/rent, phone, internet and memberships from imported/bank history;
- suggest recurring expenses for user confirmation;
- merchant normalisation;
- categorisation rules;
- spending trends;
- abnormal-spending detection;
- do not automatically create commitments without user approval.

### v0.11.0 - Goals & Financial Planning

Savings targets, sinking funds, target dates, required contributions, goal forecasting and planning for irregular costs such as registration, insurance, Christmas, school expenses, holidays and home maintenance.

### v0.12.0 - Australian Open Banking / CDR

Future Australian Consumer Data Right / Open Banking support:
- account discovery;
- balance synchronisation;
- transaction synchronisation;
- incremental updates;
- duplicate prevention;
- connection health;
- manual and automatic refresh;
- integration with the import/reconciliation pipeline.

Do not implement bank credential scraping. Future bank connectivity must use appropriate Australian Open Banking/CDR providers and security practices.

### v0.13.0 - Forecast & Scenario Intelligence

Saved scenarios, scenario comparisons, long-range forecasts, forecast accuracy tracking and explainable scenario intelligence.

### v0.14.0 - Insights & Financial Health

Explainable insights including savings rate, spending pressure, expensive-period detection, budget risk, category trends, recurring expense increases, income changes, projected savings rate, high-expense periods, cash-flow pressure periods and year-end projections.

### v0.15.0 - Home Assistant Integration

Planned sensors/entities:
- current household balance;
- forecast 30-day balance;
- forecast year-end balance;
- next bill;
- next income;
- bills due this week;
- Planned Spending this month;
- lowest forecast balance;
- projected shortfall date;
- category budget remaining;
- monthly net cash flow;
- useful dashboard cards and automations.

### v1.0.0 - Production Release

Reliability, security hardening, onboarding, performance, backup/recovery, documentation, accessibility and production-quality Home Assistant install/update experience.

## CSV import and recurring-cost discovery requirements

CSV bank transaction imports will eventually be used to compare planned versus actual spending, match imported transactions against expected income, recurring expenses, bills, forecast occurrences and planned purchases, detect duplicates and suggest recurring expenses from transaction history.
