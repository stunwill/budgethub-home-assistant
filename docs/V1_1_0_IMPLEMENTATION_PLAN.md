# Fynvo v1.1.0 Implementation Plan

Status: In development

Theme: Security, Transaction & Financial Data Coverage Foundations

This release is the first post-v1.0 feature release. It builds on the merged v1.0.0 production baseline and focuses on four connected foundations:

1. Financial Data Coverage and import provenance
2. Transaction splitting
3. MFA / stronger authentication
4. Data portability

## Repository findings

The merged repository already contains:

- account-bound CSV import preview/commit;
- import batches and import history;
- imported transaction provenance via `transactions.import_batch_id`, `source`, `external_id` and `import_date`;
- duplicate detection and reconciliation suggestions;
- Home Assistant administrator bootstrap/recovery and server-side sessions;
- provider-neutral banking foundations from v0.12.0;
- local CI validation and v1.0 acceptance documentation.

The implementation should extend those structures rather than create parallel systems.

## Financial Data Coverage

Introduce a source-neutral coverage model that distinguishes transaction span from confirmed source coverage.

Required concepts:

- `transaction_span_start` / `transaction_span_end`: derived from successfully accepted imported rows;
- `coverage_status`: `unknown`, `partial`, `confirmed`;
- `coverage_start` / `coverage_end`: user-confirmed or source-confirmed range;
- deterministic aggregate coverage intervals per Account;
- known gaps and current/continuous quality summaries;
- provenance back to all contributing import batches.

Manual transactions do not automatically establish complete source coverage.

The first UI should live under Import & Data and expose an Account-level year timeline with Jan-Dec month segments and real day-proportional placement. Unknown, partial and confirmed ranges must be visually and semantically distinct. Desktop hover, keyboard focus and mobile tap must expose provenance and a route to Import Detail.

## Import Detail

Each import batch should expose an authenticated detail endpoint/page containing:

- filename;
- Account;
- source type;
- import timestamp;
- row/import/duplicate/rejected/matched counts;
- transaction span;
- confirmed coverage range/status;
- credits, debits and net movement;
- imported transaction list;
- links back to normal Transaction workflows.

Raw CSV retention is not required. Processed provenance is authoritative.

## Transaction splits

Introduce first-class child allocations in integer cents. The parent transaction remains the authoritative Account-balance and reconciliation record. Split allocations drive Category/Budget reporting and must sum exactly to the parent amount.

## MFA

Add standards-based local TOTP MFA without a mandatory cloud dependency. Preserve Home Assistant ingress and administrator recovery. Recovery must be able to safely clear MFA state. Secrets must never be logged or returned to ordinary frontend APIs.

## Data portability

Add authenticated structured export foundations for Accounts, Cards, Transactions, splits, Categories, Income, Bills, Recurring Expenses, Planned Spending, Budgets, Goals, Scenarios, import provenance, coverage metadata and reconciliation relationships. JSON should preserve relationships that flat CSV cannot.

## Approved post-v1 roadmap

- v1.1.0 Security, Transaction & Financial Data Coverage Foundations
- v1.2.0 Household Identity & Access
- v1.3.0 Household Permissions, Audit Events & Change History
- v1.4.0 Home Assistant Financial Integration
- v1.5.0 Australian Open Banking Foundation
- v1.6.0 Open Banking Pilot Sync
- v1.7.0 Open Banking Reliability & Reconciliation
- v1.8.0 Reporting & Household Financial Snapshot
- v1.9.0 Open Fynvo Platform
- v2.0.0 Wealth & Whole-Household Finance

## Release gates

The release is not complete until backend, frontend and Home Assistant CI pass, v1.0-to-v1.1 migration/data preservation is tested, Home Assistant ingress remains functional, and release metadata/changelog/roadmap are updated.
