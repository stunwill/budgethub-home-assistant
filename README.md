# Fynvo

**Fynvo** is a Home Assistant add-on for household cash-flow forecasting, accounts, transactions, recurring expenses, planned spending and future financial insight.

> Know what's coming.

## Current release

Current development target: **v0.3.0 Accounts & Transactions**.

v0.3.0 adds the core financial ledger:

- accounts;
- opening balances;
- calculated balances;
- manual income and expense transactions;
- account-to-account transfers;
- running balances;
- dashboard financial position using real account data;
- release changelog requirements.

## Architecture

- FastAPI backend
- React/Vite frontend
- SQLite database stored under `/data`
- Docker-based Home Assistant add-on
- Home Assistant Ingress UI

The financial domain is intentionally kept separate from Home Assistant deployment concerns so Fynvo can later support standalone Docker, PWA/mobile clients, external integrations, CSV import, Australian Open Banking/CDR and hosted deployment.

## Authentication

Fynvo requires authentication before access to financial information.

On first run, create the initial administrator account through the Fynvo setup screen. Fynvo stores salted PBKDF2 password hashes and server-side sessions in SQLite.

## Home Assistant installation

Add this repository to Home Assistant:

```text
https://github.com/stunwill/fynvo-home-assistant
```

Then install and open the **Fynvo** add-on.

## Changelog and releases

Starting with v0.3.0, every release must include:

- `CHANGELOG.md` entry;
- Home Assistant-visible release notes;
- Git tag;
- GitHub Release;
- user-readable release notes.

See `docs/RELEASE_PROCESS.md`.

## Roadmap

See [`docs/FYNVO_PRODUCT_ROADMAP.md`](docs/FYNVO_PRODUCT_ROADMAP.md).
