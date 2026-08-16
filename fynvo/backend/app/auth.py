from datetime import timedelta
from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from .config import get_settings
from .database import get_db
from .models import LoginAttempt, Session, User
from .security import expiry_from_now, hash_password, hash_token, new_session_token, utcnow, verify_password


def get_client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def setup_required(db: DbSession) -> bool:
    return db.scalar(select(func.count(User.id))) == 0


def is_rate_limited(db: DbSession, username: str, client_key: str) -> bool:
    settings = get_settings()
    window_start = utcnow() - timedelta(seconds=settings.login_attempt_window_seconds)
    count = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.username == username,
            LoginAttempt.client_key == client_key,
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at >= window_start,
        )
    )
    return bool(count and count >= settings.max_login_attempts)


def record_login_attempt(db: DbSession, username: str, client_key: str, success: bool) -> None:
    db.add(LoginAttempt(username=username, client_key=client_key, success=success))
    db.commit()


def create_initial_admin(db: DbSession, username: str, password: str, display_name: str) -> User:
    if not setup_required(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Initial setup has already been completed")
    user = User(
        username=username.strip().lower(),
        display_name=display_name.strip() or username.strip(),
        password_hash=hash_password(password),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: DbSession, username: str, password: str, client_key: str) -> User:
    username_normalised = username.strip().lower()
    if is_rate_limited(db, username_normalised, client_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed login attempts. Try again later.")
    user = db.scalar(select(User).where(User.username == username_normalised, User.is_active.is_(True)))
    if user is None or not verify_password(password, user.password_hash):
        record_login_attempt(db, username_normalised, client_key, success=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    record_login_attempt(db, username_normalised, client_key, success=True)
    return user


def start_session(response: Response, db: DbSession, user: User) -> str:
    settings = get_settings()
    token = new_session_token()
    db.add(Session(token_hash=hash_token(token), user_id=user.id, expires_at=expiry_from_now(settings.session_expiry_minutes)))
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.session_expiry_minutes * 60,
        path="/",
    )
    return token


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.session_cookie_name, path="/")


def get_current_user(
    response: Response,
    db: DbSession = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias="fynvo_session"),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = db.scalar(select(Session).where(Session.token_hash == hash_token(session_token)))
    if session is None or session.revoked_at is not None or session.expires_at <= utcnow():
        clear_session_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    user = db.scalar(select(User).where(User.id == session.user_id, User.is_active.is_(True)))
    if user is None:
        clear_session_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def revoke_current_session(response: Response, db: DbSession, token: str | None) -> None:
    if token:
        session = db.scalar(select(Session).where(Session.token_hash == hash_token(token)))
        if session:
            session.revoked_at = utcnow()
            db.commit()
    clear_session_cookie(response)
