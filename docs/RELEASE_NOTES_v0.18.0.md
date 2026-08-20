# Fynvo v0.18.0 Release Notes

## Financial Data Integrity, Category Management & Workflow Polish

Fynvo v0.18.0 focuses on making the existing household-finance model safer to maintain before additional production bank integrations are introduced.

### Category management

- Category create/edit now uses a normalised comparison that ignores case, leading/trailing whitespace and repeated whitespace.
- A new Merge Category workflow previews affected financial records before applying changes.
- Merges reassign linked records and deactivate the source Category rather than deleting financial history.
- Parent merges safely consolidate same-name child Categories under the destination.
- A Category Data health check identifies duplicate Categories, orphan relationships, circular hierarchy, inactive/missing references, stale denormalised Category paths and Category-type conflicts.
- The Categories page is more compact on mobile and reduces repeated zero-entry visual clutter.

### Recurring expenses and commitments

- Possible duplicate Recurring Expenses are detected using normalised name, amount, frequency, payment source and due-date proximity.
- Duplicate detection is advisory only. Fynvo does not automatically merge Recurring Expenses.
- Upcoming Commitments has a provider-neutral filtering/service foundation and duplicate-suppression helper.
- Existing linked Bill/Recurring Expense suppression remains authoritative for scheduled events.
- Existing effective-dated recurring amount changes remain intact so future amount changes do not rewrite history.

### Accounts and Cards

- Added integrity diagnostics for Cards referencing missing Accounts and active Cards linked to archived Accounts.
- Existing Card-to-Account derivation for card-paid Recurring Expenses remains the authoritative relationship. A selected Card determines its linked Account.

### Income and mobile workflow

- The Income page remains free of the global Date Range control introduced on forecasting views.
- Mobile financial record spacing is tightened to reduce unnecessarily tall cards and rows.

### Quality gates

A new `scripts/ci-local.sh` helper runs the same core validation expected by CI:

- Python compilation
- Ruff
- backend tests
- application import
- frontend tests
- frontend production build
- Home Assistant metadata validation
- Docker image build

### Out of scope

v0.18.0 does not add direct ING connectivity, a new production Open Banking/CDR provider, bank credential storage or a standalone Cloudways deployment.
