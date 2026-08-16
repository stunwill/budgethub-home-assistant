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

A budget is how much the user intends or allows themselves to spend for a category, account, household member, period or goal. Budgets are targets and constraints.

### Planned

Planned is what the user currently expects to spend or receive. Planned entries include known future purchases, forecast income and known recurring commitments. Planned values may change as the user moves dates, changes priorities or excludes items from forecasts.

### Actual

Actual is what really occurred based on recorded, imported or reconciled transactions. Actuals are used to compare against budgets and planned activity.

Fynvo must preserve the distinction between these three concepts in the data model, UI and reporting.

## Release plan

### v0.2.0 - Fynvo Foundation + Dashboard

Product outcome: product architecture, authentication, rebrand and financial overview.

Scope:
- complete Fynvo rebrand
- Home Assistant add-on foundation
- standalone-friendly backend/frontend structure
- SQLite persistence under `/data`
- first-run administrator setup
- username/password login
- secure password hashing
- server-side session enforcement
- logout and password change
- protected financial API endpoints
- responsive application shell
- Overview dashboard with real-data empty states
- AUD and Australia/Melbourne defaults
- security and architecture documentation

Deferred: real accounts, transactions, income schedules, recurring expenses, planned spending records and forecast engine.

### v0.3.0 - Accounts & Transactions

Product outcome: core financial ledger.

Planned scope:
- create and manage accounts
- account opening/current balance fields
- manual transaction creation and editing
- transaction types for income, expense and transfer
- transaction dates, descriptions, merchant/payee and notes
- account-level dashboard summaries
- protected ledger APIs
- database migrations for accounts and transactions

### v0.4.0 - Income & Recurring Expenses

Product outcome: predictable household income and commitments.

Planned scope:
- recurring income sources
- recurring expenses and subscriptions
- weekly, fortnightly, monthly, quarterly, six-monthly, annual and custom recurrence rules
- next due/payment dates
- due-date warnings
- archive/inactive states
- generation of expected future occurrences

### v0.5.0 - Planned Spending

Product outcome: future discretionary purchases and commitments.

Planned scope:
- planned spending items
- optional planned dates
- estimated amounts
- priorities and status
- include/exclude from forecast
- undated wishlist items
- dashboard Top Planned Spending integration

### v0.6.0 - Cash Flow Forecasting

Product outcome: forecast future financial position.

Planned scope:
- dated forecast engine
- combine current balances, income, recurring expenses and planned spending
- 30/60/90 day and custom ranges
- projected balance chart
- low-balance warnings
- explainable forecast entries

### v0.7.0 - Calendar & Categories

Product outcome: financial calendar and reusable classification.

Planned scope:
- monthly calendar view
- transaction/category management
- category filters
- calendar event detail modal
- reusable labels/tags
- category-level dashboard summaries

### v0.8.0 - Budgeting

Product outcome: budget, planned and actual spending management.

Planned scope:
- category budgets by month/pay cycle
- compare budgeted vs planned vs actual
- surplus/deficit indicators
- rolling budget periods
- budget dashboard cards

### v0.9.0 - CSV Import & Reconciliation

Product outcome: import bank transactions and compare planned vs actual.

Planned scope:
- upload bank CSV files
- configurable import mappings
- duplicate import detection
- imported transaction review queue
- match imported transactions against expected income, recurring expenses and planned purchases
- identify unmatched transactions
- compare planned versus actual spending

### v0.10.0 - Recurring Cost Discovery

Product outcome: detect recurring expenses missing from Fynvo.

Planned scope:
- analyse imported transaction history
- identify likely recurring expenses that have not been entered
- recommend recurring-expense creation
- confidence indicators and review workflow
- ignore/dismiss rules

### v0.11.0 - Reports & Analytics

Product outcome: trends, comparisons and financial reporting.

Planned scope:
- monthly and annual reports
- income/expense trends
- category comparisons
- budget variance reports
- recurring-cost change history
- exportable summaries

### v0.12.0 - Goals & Savings

Product outcome: savings targets and contribution planning.

Planned scope:
- savings goals
- target amounts and target dates
- contribution calculations
- link planned purchases to savings goals
- goal priority and progress tracking

### v0.13.0 - Debt Planner

Product outcome: loans, mortgages and debt strategies.

Planned scope:
- debt accounts
- repayments and interest assumptions
- mortgage/loan tracking
- extra repayment scenarios
- debt payoff projections

### v0.14.0 - Household Finance

Product outcome: multi-user and shared/private finances.

Planned scope:
- multiple users
- household membership
- shared and private accounts/items
- roles and permissions
- user-specific dashboard views

### v0.15.0 - Home Assistant Integration

Product outcome: sensors, services, dashboards and automations.

Planned scope:
- Home Assistant sensors for key Fynvo metrics
- services for adding planned spending or transactions
- notifications for upcoming large expenses
- dashboard cards
- optional Home Assistant authentication integration

### v0.16.0 - Financial Intelligence

Product outcome: contextual financial insights.

Planned scope:
- explain upcoming pressure points
- highlight unusually high costs
- contextual warnings and recommendations
- safe, auditable insight generation

### v0.17.0 - Scenario Planning

Product outcome: what-if financial modelling.

Planned scope:
- compare multiple scenarios
- move planned purchases and see forecast impact
- temporary income/expense changes
- side-by-side forecast comparison

### v0.18.0+ - Connected Banking

Product outcome: Australian Open Banking/CDR and automated feeds.

Planned scope:
- investigate Australian CDR/Open Banking providers
- bank-feed connection model
- consent and token storage strategy
- automated transaction ingestion
- reconciliation against expected items
- robust privacy and security review

## CSV import and recurring-cost discovery requirements

CSV bank transaction imports will eventually be used to:

- compare planned versus actual spending;
- match imported transactions against expected income, recurring expenses and planned purchases;
- detect duplicate imports;
- identify transactions that cannot be matched;
- detect likely recurring expenses that have not been entered into Fynvo;
- recommend creation of new recurring expenses based on transaction history.

## Known v0.2.0 security limitations

- MFA, passkeys, OAuth/SSO and Home Assistant authentication integration are not yet implemented.
- Cookie `secure` mode is not forced in v0.2.0 because local/Home Assistant ingress deployments commonly run behind local HTTP or reverse proxies. This must be revisited before hosted/cloud deployment.
- Rate limiting is local-database-backed and intended as basic brute-force protection, not distributed abuse prevention.
