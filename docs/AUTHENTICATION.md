# Fynvo Authentication

Fynvo uses local username/password authentication for the dashboard and protected financial API endpoints.

## First-run administrator bootstrap

From v0.12.0, Home Assistant add-on installations should configure the first administrator in the add-on Configuration page.

Required bootstrap fields:

- `admin_username`
- `admin_display_name`
- `admin_password`

Optional fields:

- `admin_recovery_mode`
- `session_days`

When no users exist and valid administrator bootstrap configuration is present, Fynvo creates the first administrator automatically. The created user can then log in through the normal login page.

If no users exist and bootstrap configuration is missing, Fynvo reports that administrator setup is required and explains that the owner should configure the administrator in Home Assistant and restart Fynvo.

## No default password

Fynvo does not ship with a permanent default such as `admin/admin` or `admin/password`.

Do not commit real passwords to Git. Use the Home Assistant add-on Configuration page or environment variables supplied by the deployment environment.

## Password storage

Passwords are never stored in plaintext. Fynvo stores a salted PBKDF2-SHA256 password hash in the local SQLite database under the persistent add-on `/data` directory.

## Bootstrap behaviour after setup

Bootstrap configuration is intended for initial setup only.

After an administrator exists:

- stored password hashes are used for login;
- changing `admin_password` does not silently reset the account;
- restarting the add-on does not duplicate the administrator;
- the existing database remains authoritative.

## Administrator recovery

If the owner is locked out:

1. Set `admin_username` to the administrator account to recover.
2. Set `admin_display_name` as required.
3. Set `admin_password` to a temporary recovery password.
4. Set `admin_recovery_mode` to `true`.
5. Restart Fynvo.
6. Log in using the recovery password.
7. Turn `admin_recovery_mode` back to `false` and restart Fynvo.
8. Change the password from inside Fynvo if required.

Recovery mode is explicit. Normal restarts do not reset the password.

## Sessions

Successful login creates a server-side session and sends the browser an HttpOnly `fynvo_session` cookie. The session token itself is not stored in plaintext; Fynvo stores only a SHA-256 hash of the token.

Sessions expire automatically. Logout revokes the current server-side session and clears the browser cookie.

## Protected APIs

Financial endpoints are protected with the same backend user dependency. The application returns authentication errors for unauthenticated access and avoids exposing internal security details in login failures.

## Future authentication roadmap

The data model is intended to support later additions such as multiple users, roles, household membership, deactivation/reactivation, password reset, last login, activity history, MFA, passkeys, SSO/OAuth and Home Assistant authentication integration.
