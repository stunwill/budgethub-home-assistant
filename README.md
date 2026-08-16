# BudgetHub

BudgetHub is a Home Assistant add-on for household budgeting, recurring expenses, recurring income, planned purchases and forward cash-flow forecasting.

## Goals

BudgetHub is designed to answer practical household finance questions such as:

- What bills are coming up?
- When is the next salary payment?
- What will the projected balance be in 30, 60 or 90 days?
- What happens if a planned purchase is added, moved or removed?
- How much should be set aside for large annual or irregular costs?

## v0.1.0 scope

The first release establishes the application foundation and will support:

- recurring expenses
- recurring income
- planned purchases
- dated cash-flow forecasting
- dashboard summaries
- local SQLite persistence
- Home Assistant Ingress
- AUD currency
- Australia/Melbourne timezone

Bank feeds and Google Sheets are intentionally outside the initial release.

## Architecture

- FastAPI backend
- React/Vite frontend
- SQLite database stored under `/data`
- Docker-based Home Assistant add-on
- Home Assistant Ingress UI

## Roadmap

See [`docs/BUDGETHUB_PRODUCT_ROADMAP.md`](docs/BUDGETHUB_PRODUCT_ROADMAP.md).

## Status

Early development. Current target: **v0.1.0 Foundation**.
