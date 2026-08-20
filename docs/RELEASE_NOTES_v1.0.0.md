# Fynvo v1.0.0 Release Notes

## Stable Production Release

Fynvo v1.0.0 is the first stable release of the Home Assistant household-finance application. The release is deliberately focused on production readiness, validation, documentation and safe upgrade behaviour rather than major feature expansion.

### Stable baseline

v1.0.0 retains the established Fynvo workflows for Accounts, Cards, Transactions, Transfers, Income, Recurring Expenses, Bills, Planned Spending, Categories, Budgets, Forecasting, Financial Calendar, Scenarios, Goals, CSV import, reconciliation foundations, Spending Intelligence, Insights, Financial Health and Upcoming Commitments.

### Data integrity

- Category normalisation, duplicate prevention, safe Category merge and Category health diagnostics introduced in v0.18.0 remain part of the stable baseline.
- Category merges preserve linked financial history and archive the source Category rather than destructively deleting it.
- Account/Card integrity and duplicate commitment protections remain release requirements.
- Existing financial records and historical amounts must be preserved across normal upgrades.

### Production validation

The v1.0.0 release process requires:

- backend compilation, Ruff, backend regression tests and application import;
- frontend regression tests and production build;
- Home Assistant metadata/YAML validation and Docker build;
- fresh and representative upgrade/migration validation;
- documented backup/restore validation;
- authentication, session and recovery validation;
- representative mobile, tablet and desktop acceptance;
- explicit recording of any installed Home Assistant checks that remain manual.

### Backup, restore and limitations

See:

- `docs/BACKUP_RESTORE_v1.0.0.md`
- `docs/V1_ACCEPTANCE_CHECKLIST.md`
- `docs/KNOWN_LIMITATIONS_v1.0.0.md`

The release must not claim installed Home Assistant, iPhone, upgrade or restore acceptance unless those checks were actually executed.

### Deferred functionality

v1.0.0 does not introduce direct ING integration, a new production CDR/Open Banking provider, automatic production bank synchronisation, a new multi-user permissions architecture, Home Assistant financial entities or standalone Cloudways hosting. These remain post-v1 scope.
