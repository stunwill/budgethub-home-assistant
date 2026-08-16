from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DbSession

from .auth import (
    authenticate_user,
    create_initial_admin,
    get_client_key,
    get_current_user,
    revoke_current_session,
    setup_required,
    start_session,
)
from .config import APP_VERSION, get_settings
from .dashboard import get_overview
from .database import get_db, run_migrations
from .models import User
from .schemas import AuthStateResponse, DashboardResponse, LoginRequest, PasswordChangeRequest, SetupRequest, UserResponse
from .security import hash_password, verify_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(
    title="Fynvo API",
    version=APP_VERSION,
    description="Fynvo household cash-flow forecasting API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def public_user(user: User) -> UserResponse:
    return UserResponse(id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Fynvo", "version": APP_VERSION}


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}


@app.get("/api/auth/state", response_model=AuthStateResponse)
def auth_state(response: Response, db: DbSession = Depends(get_db), session_token: str | None = Cookie(default=None, alias="fynvo_session")):
    try:
        user = get_current_user(response=response, db=db, session_token=session_token)
        return AuthStateResponse(authenticated=True, setup_required=False, user=public_user(user))
    except HTTPException:
        return AuthStateResponse(authenticated=False, setup_required=setup_required(db), user=None)


@app.post("/api/auth/setup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def setup_admin(payload: SetupRequest, response: Response, db: DbSession = Depends(get_db)):
    user = create_initial_admin(db, payload.username, payload.password, payload.display_name)
    start_session(response, db, user)
    return public_user(user)


@app.post("/api/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password, get_client_key(request))
    start_session(response, db, user)
    return public_user(user)


@app.post("/api/auth/logout")
def logout(response: Response, db: DbSession = Depends(get_db), session_token: str | None = Cookie(default=None, alias="fynvo_session")):
    revoke_current_session(response, db, session_token)
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return public_user(current_user)


@app.post("/api/auth/change-password")
def change_password(payload: PasswordChangeRequest, current_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "ok"}


@app.get("/api/dashboard/overview", response_model=DashboardResponse)
def dashboard_overview(range_days: int = 90, current_user: User = Depends(get_current_user)):
    if range_days not in (30, 60, 90):
        range_days = 90
    return get_overview(range_days)


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def frontend(full_path: str):
        index = frontend_dist / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Frontend not built")
