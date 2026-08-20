# Fynvo v1.2.0 Release Notes

## Household Identity & Access

Fynvo v1.2.0 introduces the household identity foundation required for secure multi-user household finance without redesigning the existing financial model.

The release answers a new authoritative question for the backend: **who belongs to this Fynvo household?**

Comprehensive record-level financial permissions remain a v1.3.0 responsibility.

## Household identity

Each Fynvo installation now has a stable Household identity with a mutable display name, status, timezone and default currency. Renaming a Household does not change its identifier or break financial relationships.

Existing installations migrate automatically to an initial Household. Existing financial records are preserved and remain available through legacy-compatible Household Shared visibility foundations.

## Household membership

User identity is now explicitly separate from Household Membership. Membership records connect a User to the Household and carry the member's role and lifecycle status.

Initial roles are:

- Administrator
- Household Member
- Read Only

These roles are authoritative structured data. v1.2.0 uses Administrator authority for household user management and safety controls, but it does not claim complete role-based financial-record permission enforcement.

## Member management

Administrators can manage household members from the Household settings experience. The release supports:

- viewing members;
- creating a member;
- editing display name and role;
- deactivating a member;
- reactivating a member;
- resetting a member password;
- resetting MFA state where supported;
- revoking member sessions;
- viewing safe account/security status information.

Sensitive authentication material is not returned in member-list/detail responses.

## Initial password and reset workflow

New members use a temporary first-login credential rather than a permanent shared/default password. The member is required to establish a new password and the temporary credential is replaced.

Administrator password reset preserves the same User identity and historical financial attribution. It does not create a replacement account. Password reset revokes affected sessions.

Passwords remain stored as hashes. Existing passwords are never displayed to administrators.

## MFA compatibility

The v1.1.0 MFA foundation remains attached to User identity rather than Household Membership. Household users can therefore use the same MFA lifecycle without sharing MFA secrets between members.

Administrative MFA reset, where available, removes/reinitialises the user's MFA state without revealing the previous secret and revokes relevant sessions.

## Administrator safety

Fynvo prevents normal household-management operations from leaving an active Household with no active Administrator.

The only active Administrator cannot be demoted or deactivated. Those operations become available only when another active Administrator exists.

Existing administrator recovery remains part of the supported authentication architecture.

## Deactivation and reactivation

Deactivation is the normal v1.2.0 user-lifecycle operation. It is not destructive deletion.

When a member is deactivated:

- login is blocked;
- active sessions are revoked;
- the User identity remains;
- historical financial records remain;
- ownership and attribution records remain available for later Audit Events and Change History.

Reactivation reuses the same User identity and does not create duplicate users.

## Ownership and attribution foundations

v1.2.0 introduces structured foundations that keep these concepts separate:

- Household
- Owner
- Creator
- Last updater
- Visibility

Existing and newly created financial records can be associated with the Household and a legacy-compatible `household_shared` visibility state. Accounts support explicit owner metadata as an early ownership use case.

This is a metadata foundation only. Private versus Household Shared permission enforcement is intentionally deferred to v1.3.0.

## Account and Card relationships

Account ownership metadata can identify a household member separately from the actor who created or last updated the record.

Cards continue to belong to Accounts. v1.2.0 does not replace or weaken the existing Account → Card relationship.

## Transactions, imports and provenance

Household identity is layered alongside existing financial provenance rather than replacing it.

For example, an imported transaction can continue to identify its source and import batch while separately retaining the importing user and Account ownership context.

Financial Data Coverage remains Account/source based. Transaction split allocations and reconciliation remain authoritative financial behaviours and are not reinterpreted as user ownership.

## Backend household boundary

The authenticated backend establishes the current User, active Household Membership and Household context. The frontend is not trusted to select an arbitrary household identifier.

Household-management APIs enforce Administrator authority on the backend. Hiding frontend controls is not treated as a security boundary.

## Household settings UI

A responsive Household management experience is included for phone, tablet and desktop layouts, including member status, roles, security state and lifecycle actions.

The interface is designed to remain usable at narrow phone widths without introducing horizontal page overflow.

## Migration

The v1.2.0 migration is forward-only and incremental. Normal upgrade does not reset the database.

For an existing v1.1.0 installation the migration:

1. creates the initial Household;
2. creates Household Membership records for existing users;
3. keeps the existing Administrator identity;
4. preserves authentication and MFA records;
5. preserves financial records and IDs;
6. establishes Household ownership/visibility metadata without duplicating financial records;
7. advances the schema to the v1.2 household identity schema.

## Financial behaviour preserved

v1.2.0 is not a redesign of Fynvo's financial truth. Existing concepts and calculations remain separate and authoritative:

- Actual
- Committed
- Planned
- Budget
- Forecast
- Scenario

The release is intended to preserve Accounts, balances, Transactions, transfers, splits, Categories, Budgets, Income, Recurring Expenses, Bills, Planned Spending, forecasting, Goals, Scenarios, Insights, CSV import, provenance, Financial Data Coverage and reconciliation.

## Private iPhone architecture preparation

The release documents prerequisites for a future private native SwiftUI application. The intended mobile architecture reuses the same Fynvo backend, User identities, Household Memberships and financial database.

The architecture remains compatible with future:

- versioned mobile-facing APIs;
- short-lived access and revocable renewable credentials;
- iOS Keychain storage;
- Face ID protected local access;
- device/session revocation;
- local network and Tailscale access;
- offline read caching;
- idempotent mobile writes;
- notifications, widgets and App Intents later.

No native iPhone application is included in v1.2.0.

## Explicit limitations

v1.2.0 does **not** deliver:

- comprehensive record-level permissions;
- complete Private versus Household Shared enforcement;
- selected-member sharing;
- immutable Audit Events;
- comprehensive Change History;
- full User Activity;
- a native iPhone client;
- a public mobile API;
- APNs, widgets or Siri/App Intents;
- production CDR/Open Banking connectivity;
- automatic bank synchronisation;
- Home Assistant financial entities;
- standalone/cloud migration.

Those capabilities remain later-release work.

## Release validation

The v1.2.0 pull request must not be merged while required GitHub Actions checks are failing. Automated validation covers backend tests and linting, frontend tests/build, Home Assistant metadata/build and migration/security regressions available in CI.

Installed Home Assistant ingress and device-specific acceptance that cannot be executed by repository CI should continue to be recorded explicitly rather than falsely represented as automated proof.
