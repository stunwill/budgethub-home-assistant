# Bank Connections v0.12.0

## Purpose

Fynvo v0.12.0 introduces a provider-neutral Bank Connections foundation for future Australian Open Banking / Consumer Data Right integration.

The current release includes a mock provider only. Production provider integration requires CDR consent infrastructure, provider credentials and an appropriate accredited or intermediary provider.

## Provider abstraction

Bank providers are expected to support these operations:

- list institutions;
- connect / initiate consent;
- discover accounts;
- retrieve balances;
- retrieve transactions;
- refresh / sync;
- revoke / disconnect;
- report connection status.

Provider payloads are normalised before entering Fynvo's financial domain.

## Core tables

v0.12.0 adds:

- `bank_connections`
- `external_accounts`
- `bank_transaction_identities`
- `bank_sync_history`

It also extends transactions and accounts with provider metadata, pending status support, balance timestamps and connected-account status fields.

## External Account mapping

Fynvo keeps provider account identity separate from Fynvo Account identity.

This supports:

- changing providers later;
- linking a bank account to an existing Fynvo Account;
- creating a new Fynvo Account from a discovered bank account;
- ignoring accounts that should not be tracked;
- preserving CSV/manual account history.

## Transaction ingestion

Synced transactions are written to the existing `transactions` table with `source = bank_sync`.

Fynvo stores:

- provider;
- provider account ID;
- provider transaction ID;
- pending key where supplied;
- source fingerprint;
- raw description;
- normalised merchant;
- pending/cleared status;
- posted date where supplied.

## Idempotency

Repeated syncs must not duplicate household spending.

Fynvo uses provider identity and a deterministic fingerprint to recognise already-ingested transactions. Pending transactions can update to posted transactions instead of creating a second spend.

## CSV coexistence

CSV transactions remain valid historical Actuals. Bank sync is added as another Actual source rather than a replacement. Future refinements should expand duplicate matching between CSV and bank-synced Actuals.

## Transfers and credit-card payments

Internal transfers and credit-card repayments should not become household spending or income. v0.12.0 adds provider metadata and transfer-detection foundations so future releases can continue improving this safely.

## Reconciliation

Bank transactions can produce reconciliation links for:

- Bills;
- Income;
- Planned Spending.

Expected values remain on the source record. Actual values and variance are stored through reconciliation links.

## Security

Fynvo does not store bank passwords.

v0.12.0 mock provider does not use real tokens. Production adapters must not expose tokens or authorisation codes to the frontend or logs.

## Mock provider

The mock provider simulates:

- connection;
- account discovery;
- balances;
- posted transactions;
- pending transactions;
- pending-to-posted update;
- duplicate sync behaviour;
- new incremental transactions;
- disconnect preserving history.

Mock data must always be labelled as mock or development data.
