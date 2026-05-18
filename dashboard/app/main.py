import base64
from datetime import datetime, timezone
from io import BytesIO
import os

import pyotp
import qrcode
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jwt import InvalidTokenError
from pydantic import BaseModel, EmailStr

from app.auth import (
    create_access_token,
    create_two_factor_token,
    decode_token,
    hash_refresh_token,
    new_csrf_token,
    new_refresh_token,
    verify_password,
)
from app.database import db_cursor, initialize_database

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

app = FastAPI(title="Fraud Dashboard", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TwoFactorLoginRequest(BaseModel):
    two_factor_token: str
    code: str


class TotpVerifyRequest(BaseModel):
    code: str


@app.on_event("startup")
def on_startup():
    initialize_database()


def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def set_csrf_cookie(response: Response, csrf_token: str):
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookies(response: Response):
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")


def issue_session(response: Response, user: dict):
    access_token = create_access_token(user)
    refresh_token, refresh_hash, expires_at = new_refresh_token()

    with db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user["id"], refresh_hash, expires_at.replace(tzinfo=None)),
        )

    csrf_token = new_csrf_token()
    set_refresh_cookie(response, refresh_token)
    set_csrf_cookie(response, csrf_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "role": user["role"],
            "two_factor_enabled": user["two_factor_enabled"],
        },
    }


def require_csrf(request: Request, x_csrf_token: str | None):
    cookie_token = request.cookies.get("csrf_token")
    if not cookie_token or not x_csrf_token or cookie_token != x_csrf_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing access token")

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token, "access")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token") from None

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, role, totp_secret, two_factor_enabled
            FROM users
            WHERE id = %s
            """,
            (payload["sub"],),
        )
        user = cursor.fetchone()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.get("/")
def dashboard_page():
    return FileResponse("app/static/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "dashboard"}


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, password_hash, role, totp_secret, two_factor_enabled
            FROM users
            WHERE email = %s
            """,
            (payload.email,),
        )
        user = cursor.fetchone()

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user["two_factor_enabled"]:
        return {
            "requires_2fa": True,
            "two_factor_token": create_two_factor_token(user["id"]),
        }

    return issue_session(response, user)


@app.post("/api/auth/2fa/login")
def verify_login_2fa(payload: TwoFactorLoginRequest, response: Response):
    try:
        token_payload = decode_token(payload.two_factor_token, "2fa_pending")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid 2FA token") from None

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, email, role, totp_secret, two_factor_enabled
            FROM users
            WHERE id = %s
            """,
            (token_payload["sub"],),
        )
        user = cursor.fetchone()

    if user is None or not user["totp_secret"]:
        raise HTTPException(status_code=401, detail="2FA is not configured")

    if not pyotp.TOTP(user["totp_secret"]).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    return issue_session(response, user)


@app.post("/api/auth/refresh")
def refresh_session(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
):
    require_csrf(request, x_csrf_token)

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token_hash = hash_refresh_token(refresh_token)

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT rt.id, rt.user_id, rt.expires_at, rt.revoked,
                   u.email, u.role, u.two_factor_enabled
            FROM refresh_tokens rt
            JOIN users u ON u.id = rt.user_id
            WHERE rt.token_hash = %s
            """,
            (token_hash,),
        )
        row = cursor.fetchone()

        if row is None or row["revoked"]:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        expires_at = row["expires_at"].replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh token expired")

        cursor.execute("UPDATE refresh_tokens SET revoked = TRUE WHERE id = %s", (row["id"],))

    user = {
        "id": row["user_id"],
        "email": row["email"],
        "role": row["role"],
        "two_factor_enabled": row["two_factor_enabled"],
    }
    return issue_session(response, user)


@app.post("/api/auth/logout")
def logout(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
):
    require_csrf(request, x_csrf_token)

    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        with db_cursor() as cursor:
            cursor.execute(
                "UPDATE refresh_tokens SET revoked = TRUE WHERE token_hash = %s",
                (hash_refresh_token(refresh_token),),
            )

    clear_auth_cookies(response)
    return {"success": True}


@app.post("/api/auth/2fa/setup")
def setup_2fa(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    current_user: dict = Depends(get_current_user),
):
    require_csrf(request, x_csrf_token)

    secret = pyotp.random_base32()
    otp_uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user["email"],
        issuer_name="Fraud Log Pipeline",
    )

    with db_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET totp_secret = %s, two_factor_enabled = FALSE WHERE id = %s",
            (secret, current_user["id"]),
        )

    qr = qrcode.make(otp_uri)
    image = BytesIO()
    qr.save(image, format="PNG")
    qr_code = base64.b64encode(image.getvalue()).decode("ascii")

    return {
        "secret": secret,
        "otp_uri": otp_uri,
        "qr_code_data_uri": f"data:image/png;base64,{qr_code}",
    }


@app.post("/api/auth/2fa/verify")
def verify_2fa(
    payload: TotpVerifyRequest,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    current_user: dict = Depends(get_current_user),
):
    require_csrf(request, x_csrf_token)

    if not current_user["totp_secret"]:
        raise HTTPException(status_code=400, detail="2FA setup has not been started")

    if not pyotp.TOTP(current_user["totp_secret"]).verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")

    with db_cursor() as cursor:
        cursor.execute(
            "UPDATE users SET two_factor_enabled = TRUE WHERE id = %s",
            (current_user["id"],),
        )

    return {"success": True}


@app.post("/api/auth/2fa/disable")
def disable_2fa(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    current_user: dict = Depends(get_current_user),
):
    require_csrf(request, x_csrf_token)

    with db_cursor() as cursor:
        cursor.execute(
            """
            UPDATE users
            SET totp_secret = NULL, two_factor_enabled = FALSE
            WHERE id = %s
            """,
            (current_user["id"],),
        )

    return {"success": True}


@app.get("/api/dashboard/summary")
def summary(current_user: dict = Depends(get_current_user)):
    with db_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total_logs FROM access_logs")
        total_logs = cursor.fetchone()["total_logs"]

        cursor.execute("SELECT COUNT(*) AS total_alerts FROM fraud_alerts")
        total_alerts = cursor.fetchone()["total_alerts"]

        cursor.execute(
            """
            SELECT alert_type, COUNT(*) AS count
            FROM fraud_alerts
            GROUP BY alert_type
            ORDER BY count DESC
            """
        )
        by_type = cursor.fetchall()

        cursor.execute(
            """
            SELECT severity, COUNT(*) AS count
            FROM fraud_alerts
            GROUP BY severity
            ORDER BY count DESC
            """
        )
        by_severity = cursor.fetchall()

    return {
        "total_logs": total_logs,
        "total_alerts": total_alerts,
        "alerts_by_type": by_type,
        "alerts_by_severity": by_severity,
    }


@app.get("/api/dashboard/alerts")
def alerts(limit: int = 50, current_user: dict = Depends(get_current_user)):
    limit = min(max(limit, 1), 200)
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, event_type, alert_type, severity, description,
                   ip_address, endpoint, created_at
            FROM fraud_alerts
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return {"alerts": cursor.fetchall()}


@app.get("/api/dashboard/logs")
def logs(limit: int = 50, current_user: dict = Depends(get_current_user)):
    limit = min(max(limit, 1), 200)
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, event_type, ip_address, user_agent, endpoint,
                   http_method, status_code, request_payload, created_at
            FROM access_logs
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return {"logs": cursor.fetchall()}
