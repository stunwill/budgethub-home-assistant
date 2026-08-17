# Fynvo v0.12.0 Release Notes

## Overview

Fynvo v0.12.0 establishes the foundation for Australian Open Banking / Consumer Data Right integration while resolving the release-blocking administrator-access problem introduced by the login page.

The release deliberately does not pretend to provide production CDR connectivity without provider credentials, consent infrastructure or an accredited/intermediary provider. Instead it adds the provider-neutral architecture, mock provider, sync lifecycle and transaction-ingestion pipeline needed for production adapters later.

## Administrator bootstrap

Fresh Home Assistant installations can now create the first administrator through the add-on Configuration page.

Configuration fields:

- `admin_username`
- `admin_display_name`
- `admin_password`
- `admin_recovery_mode`
- `session_days`

When no users exist and valid bootstrap configuration is present, Fynvo creates the first administrator and stores only a secure password hash.

When an administrator already exists, Fynvo ignores bootstrap username/password changes. It does not silently reset the account on every restart.

## Administrator recovery

If the owner becomes locked out:

1. Set `admin_username` to the administrator account to recover.
2. Set `admin_display_name` as required.
3. Set `admin_password` to the temporary recovery password.
4. Set `admin_recovery_mode` to `true`.
5. Restart Fynvo.
6. Log in with the recovery password.
7. Turn `admin_recovery_mode` back to `false` and restart Fynvo.
8. Change the password from inside Fynvo if required.

Recovery mode is explicit so normal restarts do not destroy or reset the existing password.

## Branding

- Version metadata is now `0.12.0`.
- The Home Assistant add-on metadata remains branded as Fynvo.
- A Fynvo favicon has been added for browser surfaces.
- Existing Fynvo logo and mark SVG assets remain the primary UI brand assets.

## Bank Connections foundation

v0.12.0 adds:

- provider-neutral Bank Connection architecture;
- mock Australian bank provider;
- provider/institution discovery;
- external account discovery;
- link existing Fynvo Account;
- create new Fynvo Account from external account;
- ignore external account;
- connected-account balance metadata;
- Sync Now;
- sync history;
- disconnect without deleting historical transactions.

## Bank transaction sync

Bank-synchronised transactions are ingested into the existing Fynvo transaction table using `source = bank_sync`.

The release stores provider transaction identity separately so repeat syncs do not create duplicate spending. Pending-to-posted matching uses provider identifiers and a cautious pending key where available.

## Reconciliation and intelligence

Synced bank transactions use the same Actual transaction pipeline as manual and CSV transactions. The foundation supports:

- merchant normalisation;
- category rules;
- duplicate prevention;
- Bill reconciliation suggestions;
- Income reconciliation suggestions;
- Planned Spending reconciliation suggestions;
- expected vs actual variance preservation;
- transfer/debt-settlement foundations.

## Dashboard corrections

The Overview dashboard now clearly distinguishes:

### Upcoming, Next 7 Days

The short-term financial agenda. It can include income, bills, recurring expenses and planned spending.

### Upcoming Commitments

Outgoing obligations during the selected dashboard horizon. It includes bills, recurring expenses and committed planned spending, but excludes ordinary income.

### Overdue

Past unresolved bills and obligations. These no longer appear as future Upcoming items.

Outgoing items are displayed as negative amounts. Income is displayed as positive.

## Known limitations

- Production CDR provider integration is not included in v0.12.0.
- Mock bank data is development/test data only.
- Full user management is not yet implemented.
- Immutable audit logs and detailed record change history are future production-readiness work.
- The running Home Assistant app still needs manual acceptance checks before release tagging.
