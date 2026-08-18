# Fynvo v0.17.0

## Core Workflow Reliability, Account Management, Mobile Experience & Pre-v1.0 Hardening

v0.17.0 is a reliability release rather than a feature-expansion release.

## Account creation root cause

The backend Account create contract was already correct: `POST /api/accounts` accepts `AccountCreate`, which does not contain or require an account ID, and the database generates the persistent ID.

The failure was in the frontend generic list `+ Add` workflow. New records were opened through the edit-modal state with `row.id = null`, but the modal always submitted through `saveEdit()`. `saveEdit()` always constructed an update endpoint using `endpointFor(type, edit.row.id)` and always used HTTP `PUT`. For a new Account this produced `PUT /api/accounts/null`.

FastAPI then matched `/api/accounts/{account_id}` and attempted to parse the literal path segment `null` as the integer `account_id`, producing the reported validation error. The account payload itself was not the source of the error.

## Account create fix

The shared modal now explicitly distinguishes create from update:

- records without a persisted ID use the entity create path and HTTP `POST`;
- persisted records use the entity detail path and HTTP `PUT`;
- successful creates close the modal, reload authoritative data and display concise success feedback;
- failed creates retain modal state and show user-oriented validation messaging.

This also corrects the same latent create-via-list defect for other RecordTable entities that reused the same modal path.

## Account model hardening

Supported account identifiers now include transaction, savings, offset, credit card, cash, mortgage, personal loan, car loan, line of credit, investment, superannuation, other asset and other liability. The legacy `vehicle_loan` identifier remains accepted for existing data.

The UI presents friendly labels rather than raw identifiers.

Asset/liability semantics are explicit. Liability balances represent the positive amount owing. Users enter a liability opening balance as a positive amount and Fynvo handles transaction and net-position semantics internally.

Available Cash is intentionally limited to active Transaction, Savings, Offset and Cash accounts. Investment, Superannuation and Other Asset balances remain assets but are not treated as immediately available cash. Liability balances and available credit are not counted as Available Cash.

Internal transfers now respect asset/liability semantics. A payment from a transaction account to a credit card reduces both cash and the amount owing instead of increasing the liability balance.

Archived accounts remain available to historical reporting through `include_archived`, are excluded from ordinary active selectors/lists, and cannot receive new manual transactions or transfers.

## Financial correctness

Fynvo continues using integer cents through the backend money utility for financial persistence/calculation. Account balance tests cover opening balances, credits, debits, historical inserts/edits and decimal-cent precision.

Financial dates continue to use date-only backend fields. Frontend Australian date rendering now anchors date-only values at local midnight instead of parsing them as UTC timestamps, preventing common one-day display shifts in Australian time zones.

## Mobile hardening

The v0.16 React drawer architecture is retained and reinforced in v0.17. Mobile navigation is fixed-position, off-canvas and hidden by default under the mobile breakpoint. The open-state class is the only mobile path that exposes the drawer. Backdrop, destination selection, close control and Escape dismissal remain supported, with background scroll locking and safe-area handling.

Mobile page actions are more compact, Accounts prioritises its list/add action, modal actions remain reachable on small screens, and Account forms use friendly account labels and liability guidance.

## Authentication and Home Assistant

The v0.15 administrator lifecycle, recovery, session and logout implementation is unchanged by v0.17 and remains covered by the backend regression suite.

Fynvo remains a Home Assistant ingress add-on on port 8097.

The actual merged v0.16 repository does not contain the previously proposed Home Assistant financial sensor/entity implementation. v0.17 therefore does not claim or fabricate regression coverage for financial entities/actions that are absent from merged source.

## Automated regression coverage

v0.17 adds regression coverage for:

- the exact `Kristy - Main AC` Account creation case;
- generated Account ID and persistence in Account listing;
- editing the same Account without duplication;
- opening-balance plus representative credit/debit calculation;
- account type metadata;
- Available Cash versus non-liquid assets/liabilities;
- liability classification;
- payment transfer into a liability;
- archived-account selector/write protection;
- frontend create modal using POST instead of PUT with a null ID;
- friendly Account type labels;
- user-facing validation messaging;
- reinforced mobile drawer closed/open contracts.

## Manual release gates

Before v0.17.0 is considered fully accepted in the installed product, complete the Account creation, iPhone/Home Assistant ingress, authentication, v0.16 upgrade and data-integrity acceptance gates documented in the release PR and `docs/V1_READINESS_v0.17.0.md`.

v1.0.0 should not be tagged until those gates pass.
