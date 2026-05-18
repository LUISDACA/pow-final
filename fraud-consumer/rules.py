from collections import defaultdict
from datetime import datetime, timedelta, timezone

failed_login_attempts = defaultdict(list)
api_requests = defaultdict(list)


def now_utc():
    return datetime.now(timezone.utc)


def detect_sql_injection(log: dict):
    payload = str(log.get("request_payload", "")).lower()

    suspicious_patterns = [
        "union select",
        "or 1=1",
        "--",
        "/*",
        "drop table",
        "information_schema",
        "sleep(",
        "benchmark(",
    ]

    for pattern in suspicious_patterns:
        if pattern in payload:
            return {
                "alert_type": "SQL_INJECTION_ATTEMPT",
                "severity": "HIGH",
                "description": f"Suspicious SQL pattern detected: {pattern}",
            }

    return None


def detect_brute_force(log: dict):
    if log.get("event_type") != "AUTH_FAILED":
        return None

    ip_address = log.get("ip_address", "unknown")
    now = now_utc()

    failed_login_attempts[ip_address].append(now)
    failed_login_attempts[ip_address] = [
        item
        for item in failed_login_attempts[ip_address]
        if item > now - timedelta(minutes=1)
    ]

    if len(failed_login_attempts[ip_address]) >= 5:
        return {
            "alert_type": "BRUTE_FORCE_ATTEMPT",
            "severity": "HIGH",
            "description": "More than 5 failed login attempts in 1 minute",
        }

    return None


def detect_scraping(log: dict):
    if log.get("event_type") != "API_ACCESS":
        return None

    ip_address = log.get("ip_address", "unknown")
    now = now_utc()

    api_requests[ip_address].append(now)
    api_requests[ip_address] = [
        item
        for item in api_requests[ip_address]
        if item > now - timedelta(minutes=5)
    ]

    if len(api_requests[ip_address]) >= 30:
        return {
            "alert_type": "SCRAPING_ATTEMPT",
            "severity": "MEDIUM",
            "description": "High request rate detected from same IP",
        }

    return None


def analyze_log(log: dict):
    alerts = []

    for detector in (detect_sql_injection, detect_brute_force, detect_scraping):
        alert = detector(log)
        if alert:
            alerts.append(alert)

    return alerts
