# Fynvo Authentication

Fynvo v0.2.0 introduces local authentication for the dashboard and protected financial API endpoints.

## First-run setup

When no user exists, Fynvo reports `setup_required: true` from `/api/auth/state` and the frontend shows the initial administrator setup screen.

The first user created becomes the local administrator. The password must be at least eight characters.

## Password storage

Passwords are never stored in plaintext. Fynvo stores a salted PBKDF2-SHA256 password hash in the local SQLite database under the persistent add-on `/data` directory.

## Sessions

Successful login creates a server-side session and sends the browser an HttpOnly `fynvo_session` cookie. The session token itself is not stored in plaintext; Fynvo stores only a SHA-256 hash of the token.

Sessions expire automatically. Logout revokes the current server-side session and clears the browser cookie.

## Protected APIs

The following endpoints are protected:

- `/api/auth/me`
- `/api/auth/change-password`
- `/api/dashboard/overview`

Future financial APIs should use the same backend dependency that protects the dashboard endpoint.

## Future authentication roadmap

The data model is intended to support later additions such as multiple users, roles, household membership, MFA, passkeys, SSO/OAuth and Home Assistant authentication integration.
