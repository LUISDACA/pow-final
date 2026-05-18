from datetime import datetime, timezone

from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.kafka_client import send_log

app = FastAPI(
    title="Fraud Log Producer API",
    version="1.0.0",
)


class LoginRequest(BaseModel):
    email: str
    password: str


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
    Laboratory-only endpoint for controlled SQL injection detection demos.
    It does not execute SQL; it emits a log with the received payload.
    """
    log = build_log(
        request=request,
        event_type="SQLI_TEST",
        endpoint="/lab/vulnerable-search",
        method="GET",
        status_code=200,
        payload={"username": username},
    )
    send_log("logs.sql_injection", log)

    return {
        "message": "Laboratory endpoint executed",
        "received_username": username,
    }
