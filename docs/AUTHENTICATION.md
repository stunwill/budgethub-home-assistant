# Fynvo Authentication

Fynvo uses local username/password authentication for the dashboard and protected financial API endpoints.

## v0.15.0 authentication lifecycle

From v0.15.0, administrator bootstrap and recovery are initialised during FastAPI application lifespan before Fynvo begins serving requests. Login and auth-state routes no longer perform administrator credential mutation as a side effect.

The lifecycle is deterministic and records a safe status such as:

- `BOOTSTRAP_REQUIRED`
- `READY`
- `READY_WITH_CONFIGURATION_WARNING`
- `RECOVERY_REQUIRED` during an active recovery transition
- `AUTH_CONFIGURATION_ERROR`

The persisted financial database remains the source of user identity and ownership. Home Assistant configuration provides intentional bootstrap/recovery input.

## First-run administrator bootstrap

Home Assistant add-on installations configure the first administrator in the add-on Configuration page.

Required bootstrap fields:

- `admin_username`
- `admin_display_name`
- `admin_password`

Optional fields:

- `admin_recovery_mode`
- `session_days`

When no users exist and valid administrator configuration is present, Fynvo creates the first active administrator during startup. First login can then succeed without visiting a setup endpoint first.

If no users exist and valid bootstrap configuration is missing, Fynvo reports that administrator setup is required.

## No default password

Fynvo does not ship with a permanent default administrator credential.

Do not commit real passwords to Git. Use the Home Assistant add-on Configuration page or deployment-provided environment variables.

## Password storage

Passwords are never stored in plaintext. Fynvo uses its established salted PBKDF2-SHA256 password hashing. Passwords and password hashes are not returned by authentication diagnostics or written to logs.

## Normal restart behaviour

When an administrator already exists and `admin_recovery_mode` is false, Fynvo does not replace the stored password on every restart.

If the configured Home Assistant administrator identity or credential fingerprint differs from the persisted administrator, Fynvo keeps the persisted credential authoritative and records a configuration warning. Recovery must be intentionally enabled to replace credentials.

## Administrator recovery

Use recovery when the configured Home Assistant administrator credentials must replace the persisted administrator credentials:

1. Enter the desired administrator username, display name and password in the Fynvo add-on Configuration page.
2. Enable `admin_recovery_mode`.
3. Save the configuration.
4. Restart Fynvo.
5. Confirm the Fynvo log reports authentication initialisation and successful administrator recovery.
6. Log in through Home Assistant ingress using the configured credentials.
7. Disable `admin_recovery_mode` after confirming access.
8. Save and restart Fynvo.
9. Confirm the same credentials still work after recovery mode is disabled.

Recovery updates the selected administrator **in place**. It does not delete and recreate the user, so the administrator primary key and financial ownership relationships remain intact.

Successful recovery also revokes all existing sessions for that administrator and clears stale failed-login state for the recovered identity. Sessions and failed-attempt state belonging to unrelated users are not cleared.

Leaving recovery mode enabled is not destructive, but Fynvo shows a signed-in warning because recovery mode should be disabled after access is confirmed.

## Recovery target selection

Fynvo does not guess which administrator to replace.

Recovery selects:

1. an existing administrator whose username exactly matches the configured username;
2. otherwise, the only administrator if exactly one administrator exists.

Recovery fails safely when multiple administrators exist and there is no exact administrator match. It also fails if the configured username belongs to a different non-administrator user.

## Configuration loading

Fynvo checks the supported runtime configuration sources, including an explicit `FYNVO_OPTIONS_FILE`, the active data directory `options.json`, and `/data/options.json`.

Startup logs may show the selected configuration source, configured username, whether username/password values are present, recovery mode and session days. The password value and option payload are never logged.

## Troubleshooting: configured administrator credentials do not work

Do not delete the database, edit SQLite manually, reinstall Fynvo, expose port 8097 to the LAN or disable authentication.

Use this sequence:

1. Verify the intended administrator values are saved in the Home Assistant add-on Configuration page.
2. Enable `admin_recovery_mode`.
3. Restart Fynvo.
4. Check startup logs for `Authentication options loaded`, `Authentication initialisation started` and `Administrator recovery completed successfully`.
5. Open Fynvo through its normal Home Assistant ingress/sidebar route and log in with the configured credentials.
6. Once access is confirmed, disable recovery mode, restart and verify login again.

If startup reports `AUTH_CONFIGURATION_ERROR`, use the safe log reason and, once signed in through an existing valid administrator session if available, `/api/auth/diagnostics`. Public pre-auth status intentionally does not expose usernames, user counts, timestamps or session information.

## Sessions

Successful login creates a server-side session and sends the browser an HttpOnly `fynvo_session` cookie. The browser token is not stored in plaintext; only its SHA-256 token hash is stored in SQLite.

`session_days` controls both cookie maximum age and server-side session expiry. Logout revokes only the current session and clears its cookie.

Credential recovery revokes all existing sessions for the recovered administrator so a session established using old credentials cannot remain valid.

## Home Assistant ingress

Fynvo remains an ingress application on port 8097. Port 8097 does not need to be exposed externally for authentication troubleshooting.

The session cookie uses path `/` and SameSite `lax` semantics so it can follow the normal Fynvo ingress navigation flow. Fynvo does not assume arbitrary forwarding headers are trustworthy for authentication or rate limiting.

## Diagnostics

Pre-authentication status exposes only:

- authentication ready/not-ready state;
- whether setup is required;
- whether recovery is required;
- whether a configuration error exists.

Authenticated administrator diagnostics can additionally show the signed-in administrator identity, administrator/active flags, whether bootstrap is configured, recovery mode, configured-identity match, last initialisation result/time, user/admin counts, options source, `session_days` and current session expiry.

No diagnostic endpoint exposes passwords, hashes, session tokens or credential fingerprints.

## Future authentication roadmap

Future production-readiness work includes household User Management, permissions, User Activity, immutable Audit Logs, record Change History, stronger recovery options and security hardening appropriate to a multi-user household deployment.
