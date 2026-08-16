# Fynvo Product Roadmap

This roadmap is the canonical development queue for Fynvo. Future development should update this file rather than creating parallel release plans.

## Product principles

1. Forecast actual dated cash flow, not just monthly averages.
2. Keep financial data local by default.
3. Separate budgeted, planned, actual and forecast financial activity.
4. Make scenario planning simple enough for everyday household use.
5. Keep financial calculations clear, auditable and explainable.
6. Support Australian household finance first while allowing later internationalisation.

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

Fynvo should learn from these capabilities while preserving its own model: Actual, Committed, Planned, Budget and Forecast remain distinct.

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

## Release definition of done from v0.3.0 onward

Every release must include a version bump, database migrations where required, automated tests, CI validation, a CHANGELOG entry, Home Assistant release notes, a Git tag, a GitHub Release and user-readable release notes.

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

Status: Implemented in the v0.6.0 development PR.

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

Product outcome: a unified timeline showing expected money entering and leaving the household.

Planned scope:
- unified financial calendar;
- income, recurring expenses, bills, Planned Spending and forecast events;
- day, week and month calendar views;
- category management improvements;
- category hierarchy where appropriate;
- category icons and visual identification;
- financial event drill-down;
- calendar-based future financial planning.

### v0.8.0 - Advanced Budgeting

Product outcome: explicit Budget vs Planned vs Forecast vs Actual comparisons.

Planned scope:
- category budgets by weekly, fortnightly, monthly, quarterly, annual and custom periods;
- annual limits with allocation/spreading strategies;
- spend-during-period, spread-weekly, spread-fortnightly, spread-monthly and allocate-to-specific-date strategies;
- rollover and non-rollover budgets;
- accumulated category balances;
- budget remaining, actual spend, planned spend, expected future spend, projected year-end spend and forecast budget variance.

Example:

```text
Groceries
Annual Budget: $12,000
Actual YTD: $8,460
Forecast YE: $13,280
Projected over budget: $1,280
```

### v0.9.0 - Transaction Import & Reconciliation

Planned scope:
- CSV transaction import;
- configurable column mapping;
- Australian date formats;
- duplicate detection;
- transaction matching and reconciliation;
- categorisation;
- recurring transaction detection;
- merchant/payee normalisation;
- import preview;
- rollback where practical;
- architecture that can later accept CDR/Open Banking data.

### v0.10.0 - Recurring Transaction Intelligence

Planned scope:
- detect subscriptions, utilities, insurance, mortgage/rent, phone, internet and memberships from imported/bank history;
- suggest recurring expenses for user confirmation;
- detect recurring expense increases;
- do not automatically create commitments without user approval.

### v0.11.0 - Reports & Analytics

Trends, comparisons, budget-vs-actual reporting, forecast accuracy reporting, net worth reporting and cash-flow reports.

### v0.12.0 - Goals, Sinking Funds & Savings

Savings targets and sinking funds for irregular and annual costs such as registration, insurance, Christmas, school expenses, holidays and home maintenance.

### v0.13.0 - Debt Planner

Loans, mortgages, repayments, payoff strategies and debt modelling.

### v0.14.0 - Household Finance

Multi-user and shared/private finances.

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
- monthly net cash flow.

### v0.16.0 - Financial Intelligence

Explainable insights including category trends, abnormal spending, recurring expense increases, income changes, projected savings rate, high-expense periods, cash-flow pressure periods, category overspend forecasts and year-end projections.

### v0.17.0 - Scenario Planning

Deeper what-if modelling, saved scenarios, scenario comparisons and scenario sharing.

### v0.18.0 - Australian Open Banking / CDR Integration

Future Australian Consumer Data Right / Open Banking support:
- account discovery;
- balance synchronisation;
- transaction synchronisation;
- incremental updates;
- duplicate prevention;
- connection health;
- manual and automatic refresh.

Do not implement bank credential scraping. Future bank connectivity must use appropriate Australian Open Banking/CDR providers and security practices.

## CSV import and recurring-cost discovery requirements

CSV bank transaction imports will eventually be used to compare planned versus actual spending, match imported transactions against expected income, recurring expenses, bills, forecast occurrences and planned purchases, detect duplicates and suggest recurring expenses from transaction history.
