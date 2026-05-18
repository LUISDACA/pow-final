import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from app.kafka_client import send_log

LAB_DB_PATH = Path("/tmp/fraud_lab.db")

app = FastAPI(
    title="Fraud Log Producer API",
    version="1.0.0",
)


class LoginRequest(BaseModel):
    email: str
    password: str


def initialize_lab_database():
    connection = sqlite3.connect(LAB_DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS lab_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )
    cursor.executemany(
        """
        INSERT OR IGNORE INTO lab_users (id, username, email, role)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "alice", "alice@example.com", "analyst"),
            (2, "bob", "bob@example.com", "viewer"),
            (3, "admin", "admin@example.com", "admin"),
        ],
    )
    connection.commit()
    connection.close()


@app.on_event("startup")
def on_startup():
    initialize_lab_database()


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_client_ip(request: Request):
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


def build_log(
    request: Request,
    event_type: str,
    endpoint: str,
    method: str,
    status_code: int,
    payload: dict,
):
    return {
        "event_type": event_type,
        "ip_address": get_client_ip(request),
        "user_agent": request.headers.get("user-agent", ""),
        "endpoint": endpoint,
        "http_method": method,
        "status_code": status_code,
        "request_payload": payload,
        "created_at": utc_now_iso(),
    }


def fetch_lab_rows(query: str, params: tuple = ()):
    connection = sqlite3.connect(LAB_DB_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    connection.close()
    return rows


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "producer-api",
    }


@app.post("/auth/login")
async def login(data: LoginRequest, request: Request):
    if data.password != "Admin123":
        log = build_log(
            request=request,
            event_type="AUTH_FAILED",
            endpoint="/auth/login",
            method="POST",
            status_code=401,
            payload={"email": data.email},
        )
        send_log("logs.auth", log)

        return {
            "success": False,
            "message": "Invalid credentials",
        }

    log = build_log(
        request=request,
        event_type="AUTH_SUCCESS",
        endpoint="/auth/login",
        method="POST",
        status_code=200,
        payload={"email": data.email},
    )
    send_log("logs.auth", log)

    return {
        "success": True,
        "message": "Login successful",
    }


@app.get("/api/products")
async def list_products(request: Request):
    log = build_log(
        request=request,
        event_type="API_ACCESS",
        endpoint="/api/products",
        method="GET",
        status_code=200,
        payload={},
    )
    send_log("logs.api", log)

    return {
        "products": [
            {"id": 1, "name": "Laptop"},
            {"id": 2, "name": "Mouse"},
            {"id": 3, "name": "Keyboard"},
        ],
    }


@app.get("/lab/vulnerable-search")
async def vulnerable_search(username: str, request: Request):
    """
    Laboratory-only endpoint.
    Intentionally vulnerable: concatenates user input into SQL.
    Do not use this pattern outside the controlled demo.
    """
    query = (
        "SELECT id, username, email, role "
        f"FROM lab_users WHERE username = '{username}'"
    )

    log = build_log(
        request=request,
        event_type="SQLI_TEST",
        endpoint="/lab/vulnerable-search",
        method="GET",
        status_code=200,
        payload={"username": username, "query": query},
    )
    send_log("logs.sql_injection", log)

    try:
        rows = fetch_lab_rows(query)
    except sqlite3.Error as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "message": "Vulnerable laboratory endpoint executed",
        "received_username": username,
        "query": query,
        "rows": rows,
    }


@app.get("/lab/safe-search")
async def safe_search(username: str, request: Request):
    """
    Repaired laboratory endpoint.
    Uses a parameterized query so SQLi payloads are treated as text.
    """
    query = "SELECT id, username, email, role FROM lab_users WHERE username = ?"

    log = build_log(
        request=request,
        event_type="SQLI_TEST_SAFE",
        endpoint="/lab/safe-search",
        method="GET",
        status_code=200,
        payload={"username": username, "query": query},
    )
    send_log("logs.sql_injection", log)

    rows = fetch_lab_rows(query, (username,))

    return {
        "message": "Safe laboratory endpoint executed",
        "received_username": username,
        "query": query,
        "rows": rows,
    }
