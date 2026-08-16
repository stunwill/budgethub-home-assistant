# Fynvo Architecture

Fynvo currently ships as a Home Assistant add-on, but the application is structured to avoid tying the financial domain to Home Assistant.

## Layers

- Frontend/UI: React/Vite application in `fynvo/frontend`.
- API: FastAPI application in `fynvo/backend/app`.
- Authentication: local setup, login, sessions and password management in `auth.py` and `security.py`.
- Persistence: SQLAlchemy models and SQLite database stored under `/data` in add-on deployments.
- Financial services: dashboard service in `dashboard.py`, with future account, transaction and forecasting services expected to live beside it.
- Deployment: Home Assistant metadata and Dockerfile under `fynvo/`.

## Persistence

The SQLite database is stored at `${FYNVO_DATA_DIR}/fynvo.sqlite3`. The Home Assistant add-on sets `FYNVO_DATA_DIR=/data`, so configuration, users and sessions survive container restarts, Home Assistant restarts and add-on upgrades.

## Architectural decisions in v0.2.0

- Implemented first-run setup rather than shipping a default password.
- Used salted PBKDF2 password hashing from the Python standard library to avoid storing plaintext passwords and avoid adding unnecessary cryptographic dependencies early.
- Stored sessions server-side and only sent opaque HttpOnly cookies to the browser.
- Kept financial dashboard values empty until account/transaction/forecasting data exists.
- Added a simple migration foundation using SQLAlchemy table creation plus `schema_version`; a fuller migration tool can be introduced when schema complexity grows.

## Future deployment targets

The structure should support standalone Docker, PWA/mobile clients, import worker services, hosted/cloud deployment and Australian CDR/Open Banking integrations without rewriting the core financial domain.
