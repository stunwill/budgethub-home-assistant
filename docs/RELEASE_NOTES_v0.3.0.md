# Fynvo v0.3.0 Release Notes

## Added

- Account management.
- Manual income and expense transactions.
- Account-to-account transfers.
- Calculated account balances and running balances.
- Dashboard financial position using real account data.
- CSV-import-compatible transaction metadata.
- Mandatory release changelog process.

## Fixed

- Root application route now returns Fynvo deterministically instead of intermittently returning HTTP 404.
- Frontend assets use a relative build base for Home Assistant ingress.
- SPA fallback supports route refresh without intercepting `/api/...`.

## Upgrade notes

Existing v0.2.0 installations migrate forward. Authentication data remains in place and the database schema is extended for accounts, transfers and transactions.

## Manual verification

After updating, open Fynvo through Home Assistant, sign in, create an account, create a transaction and refresh the page.
