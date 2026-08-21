from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DbSession

from . import intelligence, v09, v12_mount, v13_cashflow
from .auth import (
    SESSION_COOKIE,
    authenticate_user,
    create_initial_admin,
    get_client_key,
    get_current_user,
    revoke_current_session,
    setup_required,
    start_session,
)
from .config import APP_VERSION
from .dashboard import get_overview
from .database import get_db, run_migrations
from .finance import (
    annual_matrix,
    cancel_planned,
    create_bill,
    create_income,
    create_planned,
    create_recurring,
    ensure_seed_data,
    list_bills,
    list_income,
    list_planned,
    list_recurring,
    month_week_matrix,
    schedule_summary,
    today_local,
    update_planned,
)
from .forecast import (
    compare_scenario,
    create_effective_change,
    forecast_drilldown,
    generate_forecast,
    list_effective_changes,
)
from .ledger import (
    ACCOUNT_TYPES,
    archive_account,
    create_account,
    create_transaction,
    create_transfer,
    dashboard_position,
    delete_transaction,
    delete_transfer,
    get_account,
    list_accounts,
    list_transactions,
    running_transactions,
    update_account,
    update_transaction,
    update_transfer,
)
from .models import User
from .money import cents_to_decimal, parse_money
from .schemas import (
    AccountCreate,
    AccountUpdate,
    AuthStateResponse,
    BillCreate,
    DashboardResponse,
    IncomeCreate,
    LoginRequest,
    PasswordChangeRequest,
    PlannedSpendingCreate,
    PlannedSpendingUpdate,
    RecurringExpenseCreate,
    SetupRequest,
    TransactionCreate,
    TransactionUpdate,
    TransferCreate,
    TransferUpdate,
    UserResponse,
)
from .security import hash_password, verify_password

DB_DEPENDENCY = Depends(get_db)
USER_DEPENDENCY = Depends(get_current_user)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="Fynvo API", version=APP_VERSION, description="Fynvo household cash-flow forecasting API.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[], allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"])
app.include_router(v09.router)
app.include_router(intelligence.router)
app.include_router(v12_mount.router, prefix="/api")
app.include_router(v13_cashflow.router)


def public_user(user: User) -> UserResponse:
    return UserResponse(id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Fynvo", "version": APP_VERSION}


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}


@app.get("/api/auth/state", response_model=AuthStateResponse)
def auth_state(request: Request, db: DbSession = DB_DEPENDENCY):
    required = setup_required(db)
    token = request.cookies.get(SESSION_COOKIE)
    user = None
    if token:
        try:
            user = get_current_user(request, db)
        except HTTPException:
            user = None
    return AuthStateResponse(setup_required=required, authenticated=user is not None, user=public_user(user) if user else None)


@app.post("/api/auth/setup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def setup(payload: SetupRequest, response: Response, request: Request, db: DbSession = DB_DEPENDENCY):
    if not setup_required(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Fynvo is already configured")
    user = create_initial_admin(db, payload.username, payload.display_name, payload.password)
    token, expires_at = start_session(db, user, get_client_key(request))
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", expires=expires_at, secure=False)
    return public_user(user)


@app.post("/api/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, request: Request, db: DbSession = DB_DEPENDENCY):
    user = authenticate_user(db, payload.username, payload.password, get_client_key(request))
    token, expires_at = start_session(db, user, get_client_key(request))
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", expires=expires_at, secure=False)
    return public_user(user)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: DbSession = DB_DEPENDENCY):
    revoke_current_session(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@app.post("/api/auth/change-password")
def change_password(payload: PasswordChangeRequest, request: Request, response: Response, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    revoke_current_session(db, request.cookies.get(SESSION_COOKIE))
    token, expires_at = start_session(db, current_user, get_client_key(request))
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", expires=expires_at, secure=False)
    return {"status": "ok"}


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    ensure_seed_data(db, current_user)
    return DashboardResponse(**get_overview(db, current_user), position=dashboard_position(db, current_user))


@app.get("/api/accounts")
def accounts(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_accounts(db, current_user)


@app.post("/api/accounts", status_code=status.HTTP_201_CREATED)
def add_account(payload: AccountCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_account(db, current_user, payload)


@app.put("/api/accounts/{account_id}")
def edit_account(account_id: int, payload: AccountUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_account(db, current_user, account_id, payload)


@app.delete("/api/accounts/{account_id}")
def remove_account(account_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return archive_account(db, current_user, account_id)


@app.get("/api/accounts/{account_id}")
def account_detail(account_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    account = get_account(db, current_user, account_id)
    return {"id": account.id, "name": account.name, "account_type": account.account_type, "opening_balance": cents_to_decimal(account.opening_balance_cents), "is_active": account.is_active}


@app.get("/api/accounts/{account_id}/transactions")
def account_transactions(account_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return running_transactions(db, current_user, account_id)


@app.get("/api/transactions")
def transactions(account_id: int | None = None, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_transactions(db, current_user, account_id)


@app.post("/api/transactions", status_code=status.HTTP_201_CREATED)
def add_transaction(payload: TransactionCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_transaction(db, current_user, payload)


@app.put("/api/transactions/{transaction_id}")
def edit_transaction(transaction_id: int, payload: TransactionUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_transaction(db, current_user, transaction_id, payload)


@app.delete("/api/transactions/{transaction_id}")
def remove_transaction(transaction_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return delete_transaction(db, current_user, transaction_id)


@app.post("/api/transfers", status_code=status.HTTP_201_CREATED)
def add_transfer(payload: TransferCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_transfer(db, current_user, payload)


@app.put("/api/transfers/{transfer_id}")
def edit_transfer(transfer_id: int, payload: TransferUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_transfer(db, current_user, transfer_id, payload)


@app.delete("/api/transfers/{transfer_id}")
def remove_transfer(transfer_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return delete_transfer(db, current_user, transfer_id)


@app.get("/api/account-types")
def account_types(current_user: User = USER_DEPENDENCY):
    del current_user
    return {"account_types": ACCOUNT_TYPES}


@app.get("/api/income")
def income(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    ensure_seed_data(db, current_user)
    return list_income(db, current_user)


@app.post("/api/income", status_code=status.HTTP_201_CREATED)
def add_income(payload: IncomeCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_income(db, current_user, payload)


@app.get("/api/recurring-expenses")
def recurring(filter: str = "all", current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    ensure_seed_data(db, current_user)
    return list_recurring(db, current_user, filter)


@app.post("/api/recurring-expenses", status_code=status.HTTP_201_CREATED)
def add_recurring(payload: RecurringExpenseCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_recurring(db, current_user, payload)


@app.get("/api/bills")
def bills(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    ensure_seed_data(db, current_user)
    return list_bills(db, current_user)


@app.post("/api/bills", status_code=status.HTTP_201_CREATED)
def add_bill(payload: BillCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_bill(db, current_user, payload)


@app.get("/api/planned-spending")
def planned(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_planned(db, current_user)


@app.post("/api/planned-spending", status_code=status.HTTP_201_CREATED)
def add_planned(payload: PlannedSpendingCreate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_planned(db, current_user, payload)


@app.put("/api/planned-spending/{planned_id}")
def edit_planned(planned_id: int, payload: PlannedSpendingUpdate, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return update_planned(db, current_user, planned_id, payload)


@app.post("/api/planned-spending/{planned_id}/cancel")
def cancel_planned_item(planned_id: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return cancel_planned(db, current_user, planned_id)


@app.get("/api/schedule")
def schedule(start: date | None = None, days: int = Query(default=31, ge=1, le=366), current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    start = start or today_local()
    return schedule_summary(db, current_user, start, start + timedelta(days=days - 1))


@app.get("/api/schedule/year")
def schedule_year(year: int | None = None, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return annual_matrix(db, current_user, year or today_local().year)


@app.get("/api/schedule/month")
def schedule_month(year: int, month: int, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return month_week_matrix(db, current_user, year, month)


@app.get("/api/forecast")
def forecast(horizon: str = "30d", mode: str = "baseline", start: date | None = None, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return generate_forecast(db, current_user, horizon, mode, start)


@app.get("/api/forecast/drilldown")
def forecast_detail(period: str = "month", horizon: str = "90d", mode: str = "baseline", start: date | None = None, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return forecast_drilldown(db, current_user, period, horizon, mode, start)


@app.post("/api/forecast/scenario")
def forecast_scenario(payload: dict, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return compare_scenario(db, current_user, payload)


@app.get("/api/effective-amount-changes")
def amount_changes(current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return list_effective_changes(db, current_user)


@app.post("/api/effective-amount-changes", status_code=status.HTTP_201_CREATED)
def add_amount_change(payload: dict, current_user: User = USER_DEPENDENCY, db: DbSession = DB_DEPENDENCY):
    return create_effective_change(db, current_user, payload)


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
index_file = frontend_dist / "index.html"
assets_dir = frontend_dist / "assets"

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<!doctype html><title>Fynvo</title><main><h1>Fynvo</h1><p>Frontend assets are not built yet.</p></main>", status_code=200)
