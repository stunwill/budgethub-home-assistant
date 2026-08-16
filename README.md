# Fynvo

**Know what's coming.**

Fynvo is a Home Assistant add-on for household cash-flow forecasting, recurring expenses, recurring income, planned purchases and future financial overview.

## v0.2.0 scope

This combined release establishes the Fynvo product foundation and dashboard:

- Fynvo rebrand across the app, API and documentation
- Home Assistant add-on packaging
- FastAPI backend and React/Vite frontend
- SQLite persistence under the add-on `/data` directory
- first-run admin setup
- username/password login
- secure PBKDF2 password hashing
- server-side session enforcement with HttpOnly cookies
- logout and password change
- protected dashboard API
- responsive financial overview shell
- dashboard empty states for future financial modules
- AUD and Australia/Melbourne defaults

## First user setup

On first launch, Fynvo shows a setup screen. Create the initial administrator account there. The password is stored as a salted PBKDF2 hash in the local SQLite database and is never stored in plaintext.

After setup, the dashboard and protected API endpoints require authentication. Sessions are stored server-side and survive container restarts because the SQLite database is stored under `/data`.

## Architecture

Fynvo is structured so the financial domain is not unnecessarily tied to Home Assistant:

- `fynvo/frontend` - React application shell and dashboard UI
- `fynvo/backend/app` - FastAPI API, authentication and service layer
- `fynvo/backend/tests` - backend tests
- `fynvo/config.yaml` and `fynvo/build.yaml` - Home Assistant add-on metadata
- `docs/FYNVO_PRODUCT_ROADMAP.md` - canonical roadmap

The architecture is intended to support future standalone Docker, PWA/mobile clients, bank import services, hosted/cloud deployment and Australian Open Banking/CDR.

## Security notes

Fynvo v0.2.0 provides local username/password authentication, server-side sessions, password hashing, session expiry and brute-force protection. It does not yet include MFA, passkeys, roles, Home Assistant authentication integration or SSO.

## Roadmap

See [`docs/FYNVO_PRODUCT_ROADMAP.md`](docs/FYNVO_PRODUCT_ROADMAP.md).
