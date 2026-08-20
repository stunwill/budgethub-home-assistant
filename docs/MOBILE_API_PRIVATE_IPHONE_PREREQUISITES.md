# Mobile API & Private iPhone App Prerequisites

## Purpose

Fynvo v1.2.0 establishes the authoritative User, Household and Household Membership identities that a future native iPhone client must reuse. The mobile client must not create a second financial identity model or a separate authoritative financial database.

The intended architecture is:

Native SwiftUI client
→ authenticated Fynvo API
→ authenticated User and Household Membership context
→ existing Fynvo financial services
→ same authoritative Fynvo database

This document records the backend and client prerequisites that should be completed before private iPhone development begins.

## Identity and household context

The native client must authenticate as an existing Fynvo User. Household context must be resolved on the server from the authenticated User and active Household Membership. The client must not be trusted to select or override an arbitrary household identifier.

The same concepts used by the web/Home Assistant experience must remain distinct on mobile:

- User
- Household
- Household Membership
- Role
- Owner
- Creator
- Last updater
- Visibility

A future mobile client should therefore require no migration to a separate mobile user table.

## API versioning

Before mobile write APIs are considered stable, Fynvo should define an explicit API versioning policy. A versioned route family such as `/api/v1/...` is preferred for externally consumed mobile contracts, while existing internal web routes can be migrated incrementally.

The mobile contract should define stable request/response schemas, validation errors, authentication errors, pagination and compatibility expectations. Breaking API changes should require a new API version or a deliberately backwards-compatible migration path.

## Mobile authentication and session strategy

v1.2.0 deliberately preserves the existing Home Assistant/web authentication architecture. A native client should not force a premature replacement of that working session model.

Before native-client implementation, design a mobile-specific session layer that can support:

- short-lived API access credentials;
- revocable refresh credentials or an equivalent renewable session mechanism;
- per-device/session identity;
- server-side session expiry;
- explicit device/session revocation;
- password-reset and user-deactivation revocation;
- MFA-aware sign-in;
- recovery without exposing secrets.

The mobile session implementation must coexist safely with Home Assistant ingress and browser sessions.

## Keychain

Long-lived mobile authentication material must be stored in the iOS Keychain, not UserDefaults, application files, logs or a local SQLite database.

The client must never persist:

- password hashes;
- MFA secrets received from another user;
- server session secrets in plain application storage;
- administrator recovery material.

## Face ID

Face ID is a local device-access control, not a substitute for server authentication.

A suitable design is:

1. the server authenticates the Fynvo User and issues the permitted mobile session material;
2. sensitive renewable credentials are stored in the Keychain;
3. Face ID can protect access to those local Keychain items or unlock the application locally;
4. the server remains authoritative for user status, Household Membership, role, session validity and future permissions.

Deactivating a user or revoking a device must remain effective even if Face ID succeeds locally.

## Server discovery and configuration

The first private client should support an explicitly configured Fynvo server address. Future convenience options may include QR-code or guided local discovery, but discovery must not weaken authentication or allow silent connection to an untrusted server.

The client should preserve a stable server identity/configuration rather than assuming that a mutable Household name identifies a server.

## Local network access

Initial native development may target the household's local Fynvo installation. Local-network access should use the same Fynvo API and database as the Home Assistant application.

The client must handle unavailable local networking cleanly and should not silently fall back to an unrelated cloud service.

## Tailscale and private remote access

Private household use can initially use Tailscale or an equivalent private-network path before Fynvo has a public remote-access architecture. Tailscale provides network reachability only. Fynvo authentication, Household Membership and permissions must still be enforced by the backend.

The application should therefore treat local LAN and Tailscale addresses as different routes to the same authoritative server, not as different accounts or data stores.

## Device and session revocation

Before broad private testing, Fynvo should expose a Devices & Sessions capability that can identify sessions without exposing raw credentials. A user or authorised Administrator should be able to revoke an individual device/session where the final security model permits it.

At minimum, password reset, account deactivation and relevant MFA reset operations must invalidate affected mobile authentication state.

## Offline and read-cache strategy

The native app may cache read-only snapshots for responsiveness and limited offline viewing, but the cache must not become a second authoritative financial database.

An initial strategy should define:

- which financial views may be cached;
- cache expiry and invalidation;
- encryption/protection of sensitive cached data;
- what the user sees when data may be stale;
- whether logout/deactivation clears local cached data;
- conflict behaviour once writes are introduced.

Offline mutation is not required for the first private client.

## Idempotent mobile writes

Before enabling native write operations, mutating APIs should support safe retry semantics. For operations where duplicate execution would be harmful, introduce idempotency keys or another explicit request identity mechanism.

This is particularly important for unreliable mobile networks and future background operations.

## Push notifications

APNs infrastructure is not part of v1.2.0. Before push notifications are implemented, define:

- device registration and revocation;
- association between a device token, User and Household;
- notification categories and privacy rules;
- whether sensitive financial details are allowed on the lock screen;
- token rotation;
- server-side delivery architecture;
- behaviour after user deactivation or session revocation.

## Privacy

The future app must consume the same visibility and permissions policy introduced on the server. It must not implement its own interpretation of Private versus Household Shared records.

Sensitive financial information should be minimised in local logs, analytics, notifications and crash reports. No third-party telemetry should receive financial data by default without an explicit product and privacy decision.

## Prerequisites before native development

The following should be considered the minimum backend readiness for serious private iPhone development:

1. v1.2 User, Household and Membership identities are stable and migrated safely.
2. v1.3 Household permissions and privacy semantics are defined and enforced on the backend.
3. API versioning and stable mobile-facing schemas are defined.
4. A mobile session/token strategy is implemented without breaking Home Assistant ingress.
5. Device/session revocation is implemented.
6. MFA and recovery behaviour for native login is defined.
7. Local/Tailscale server configuration and TLS expectations are documented.
8. Read-cache and logout/deactivation data-clearing behaviour are defined.
9. Mutating endpoints intended for mobile have safe retry/idempotency semantics.
10. Security testing proves household isolation and record-level permissions through the mobile-facing API.

## Later mobile capabilities

The architecture should remain compatible with later additions such as:

- privately installed/TestFlight distributed SwiftUI application;
- public App Store distribution if desired later;
- widgets;
- notifications;
- App Intents and Shortcuts;
- improved remote-access architecture;
- richer offline behaviour.

None of those capabilities require a separate Fynvo financial database or separate user identity model.

## v1.2.0 non-goals

v1.2.0 does not implement the native iPhone client, a public mobile API, APNs, widgets, Siri/App Intents, a public remote-access service or comprehensive record-level permission enforcement. The purpose of this document is to keep the v1.2 identity architecture compatible with those later capabilities without destabilising the existing local-first Home Assistant application.
