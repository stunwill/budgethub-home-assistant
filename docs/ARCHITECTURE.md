# Fynvo Architecture

Fynvo is a local-first household finance application currently packaged as a Home Assistant add-on.

## Layers

- Frontend/UI: React/Vite application served by FastAPI in production.
- API: FastAPI JSON endpoints under `/api/...`.
- Authentication: username/password, salted PBKDF2 password hashes and server-side SQLite sessions.
- Financial domain: account, transaction and transfer ledger services.
- Persistence: SQLite under `${FYNVO_DATA_DIR}/fynvo.sqlite3`, `/data` in the Home Assistant add-on.
- Home Assistant deployment: add-on metadata, ingress and Docker packaging.

The account/transaction ledger intentionally avoids Home Assistant recorder/history so financial records survive recorder purges and remain portable to standalone Docker or hosted deployment.

## Accounting convention

Asset accounts use normal cash semantics:

```text
opening balance + income/credits - expenses/debits = current balance
```

Liability accounts such as credit cards and loans use balance-owed semantics:

```text
opening balance + expenses/debits - income/credits/payments = current balance owed
```

Transfers are not household income or expenditure. They are stored as one transfer record plus two linked ledger transactions.

## Home Assistant ingress

The backend listens on port `8097`, matching `fynvo/config.yaml` `ingress_port`.

The production frontend is built into `frontend/dist` and copied into the add-on image. The FastAPI server returns the SPA entry point for frontend routes such as `/`, `/login`, `/overview`, `/accounts`, `/transactions` and `/settings`, while `/api/...` remains reserved for backend routes.

The Vite frontend uses a relative base path so assets work behind Home Assistant's generated ingress path.
