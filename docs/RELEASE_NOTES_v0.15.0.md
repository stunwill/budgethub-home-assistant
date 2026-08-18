# Fynvo v0.15.0

## Authentication Reliability, Recovery Hardening & Home Assistant Integration

v0.15.0 is being delivered in two gated stages.

Priority 0 fixes the administrator bootstrap/recovery lifecycle that could leave a Home Assistant add-on installation rejecting the administrator credentials configured in the add-on Configuration page.

Priority 1, Home Assistant financial entities and automation integration, is intentionally blocked until Priority 0 passes the real Home Assistant ingress acceptance test.

## Authentication lifecycle changes

Fynvo now initialises administrator authentication during application startup rather than waiting for an authentication route to trigger bootstrap/recovery logic.

Startup now:

1. loads Home Assistant add-on options;
2. records the safe configuration source and presence metadata;
3. inspects persisted users/administrators;
4. validates bootstrap/recovery configuration;
5. deterministically selects the recovery target;
6. bootstraps or recovers the administrator where required;
7. revokes recovered-administrator sessions and clears stale failed-login state;
8. records a safe initialisation result;
9. begins serving requests only after authentication initialisation completes.

## Recovery safety

Administrator recovery updates the selected administrator in place. The user primary key is retained, preserving existing ownership relationships for financial records.

Recovery is transactional. Username, display name, active/admin flags, password hash, recovered-user session revocation, failed-attempt cleanup and recovery metadata succeed together or are rolled back.

Recovery target selection is conservative:

- exact configured administrator username match first;
- otherwise the only administrator when exactly one exists;
- multiple administrators without an exact administrator match fail safely;
- a configured username already belonging to a non-administrator fails safely.

Repeated recovery-enabled startups do not create duplicate administrators.

## Sessions and login attempts

A credential recovery revokes all existing sessions for the recovered administrator. Unrelated users' sessions are preserved.

Stale failed-login attempts associated with the recovered identity are cleared so a successful recovery is not immediately blocked by the previous lockout state. Unrelated user state is retained.

`session_days` continues to control both the browser cookie maximum age and server-side session expiry.

## Safe diagnostics and logs

Startup logging now reports:

- configuration source path;
- whether administrator username/password values are present;
- configured username;
- recovery mode;
- session days;
- persisted user/admin counts;
- bootstrap/recovery outcome;
- recovered-session revocation count;
- failed-attempt cleanup count;
- explicit safe failure reason where applicable.

Passwords, password hashes, session tokens and credential fingerprints are never logged.

Public pre-authentication status is intentionally minimal. More detailed authentication diagnostics require an authenticated administrator.

## Home Assistant ingress

Fynvo remains an ingress application on port 8097. Authentication recovery does not require exposing the port externally, deleting the Fynvo database or editing SQLite manually.

A signed-in administrator sees a dismissible warning while `admin_recovery_mode` remains enabled, reminding the administrator to disable it after confirming access.

## Mandatory recovery workflow

For a locked-out existing installation:

1. enter the desired administrator credentials in Home Assistant add-on Configuration;
2. enable `admin_recovery_mode`;
3. save and restart Fynvo;
4. confirm the startup log reports successful administrator recovery;
5. open Fynvo through Home Assistant ingress and sign in;
6. confirm Overview loads;
7. disable `admin_recovery_mode`;
8. save and restart Fynvo;
9. sign in again using the same credentials.

Both sign-ins must succeed before v0.15.0 can be considered complete.

## Automated regression coverage

The Priority 0 branch adds coverage for:

- fresh bootstrap;
- existing administrator adoption from legacy state;
- changed credentials with recovery disabled;
- recovery enabled;
- exact previously reported 401 scenario with configured recovery credentials;
- repeated recovery;
- multiple-administrator ambiguity;
- username collision with a non-administrator;
- administrator primary-key preservation;
- financial ownership preservation;
- recovered-administrator session revocation;
- unrelated-session preservation;
- stale failed-login cleanup;
- public diagnostic privacy;
- administrator-only diagnostics;
- seven-day session consistency;
- logout isolation.

## Priority 1 Home Assistant integration

Home Assistant financial entities, update semantics and automation actions remain gated. They must not be declared delivered until the authentication recovery workflow has passed in a running Home Assistant add-on through ingress.

Once that gate passes, v0.15.0 can proceed with a focused set of reliable, non-sensitive Fynvo state entities using existing authoritative Forecast, Dashboard, Budget, Goal and Insight services.

## Security

v0.15.0 does not hard-code administrator credentials, log passwords or hashes, bypass Fynvo authentication, expose port 8097 to the LAN, trust arbitrary forwarding headers, remove brute-force protection or expose full financial records through Home Assistant state.

## Release status

**In development.** Automated Priority 0 validation and real Home Assistant ingress acceptance are release gates. This release must not be marked complete while the manual ingress recovery/login test is outstanding.
