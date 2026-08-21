# Fynvo

**Fynvo** is a Home Assistant add-on for household budgeting, accounts, transactions, recurring expenses, planned spending and explainable cash-flow forecasting.

> Know what's coming.

## Current release

Current development target: **v1.3.0 Cash Flow Intelligence, Financial Calendar & Smart Forecasting**.

v1.3.0 builds on the production v1.x foundations with:

- household and per-account projected balances;
- forecast periods from 7 days to 12 months;
- account safety buffers and low-balance warnings;
- negative-balance shortfall warnings;
- overdue obligations retained in forecasts until resolved;
- occurrence-level amount, status and reschedule overrides;
- internal transfer handling with zero household net effect;
- financial calendar daily income, expense and net totals;
- grouped upcoming money views;
- isolated future-purchase affordability simulation;
- mobile-responsive cash-flow views;
- deterministic backend forecast logic with regression coverage.

Forecast values are projections based on the financial information recorded in Fynvo. They are not confirmed bank balances or guarantees of future outcomes.

## Architecture

- FastAPI backend
- React/Vite frontend
- SQLite database stored under `/data`
- Docker-based Home Assistant add-on
- Home Assistant Ingress UI

The financial domain is intentionally kept separate from Home Assistant deployment concerns so Fynvo can later support standalone Docker, PWA/mobile clients, external integrations, CSV import, Australian Open Banking/CDR and hosted deployment.

## Authentication

Fynvo requires authentication before access to financial information.

On first run, create the initial administrator account through the Fynvo setup screen. Fynvo stores salted password hashes and server-side sessions in SQLite. v1.2.0 added the Household identity and membership foundation used by later releases.

## Cash Flow Intelligence

Open **Cash Flow Intelligence** from the authenticated Fynvo shell to access:

- **Cash Flow**, projected household balances, account warnings, safety buffers and forecast breakdowns;
- **Calendar**, daily income, expense and net movement;
- **Upcoming**, grouped overdue and future financial events;
- **Can I afford this?**, an isolated future-purchase simulation that does not modify real financial records.

The v1.3 forecast API is available under `/api/v1.3/` and reuses the established Fynvo forecast, recurring expense, planned spending, bill, account and transfer foundations.

## Home Assistant installation

Add this repository to Home Assistant:

```text
https://github.com/stunwill/fynvo-home-assistant
```

Then install and open the **Fynvo** add-on.

## Changelog and releases

Every release must include:

- `CHANGELOG.md` entry;
- Home Assistant-visible release notes;
- Git tag;
- GitHub Release;
- user-readable release notes.

See `docs/RELEASE_PROCESS.md`.

## Roadmap

See [`docs/FYNVO_PRODUCT_ROADMAP.md`](docs/FYNVO_PRODUCT_ROADMAP.md).
