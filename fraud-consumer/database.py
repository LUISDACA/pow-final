import json
import os
import time

import psycopg2
from psycopg2 import OperationalError

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_password@localhost:5432/fraud_logs_db",
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def wait_for_database(max_attempts=30, delay_seconds=2):
    for attempt in range(1, max_attempts + 1):
        try:
            connection = get_connection()
            connection.close()
            print("Database connection ready.", flush=True)
            return
        except OperationalError as error:
            print(
                f"Waiting for database ({attempt}/{max_attempts}): {error}",
                flush=True,
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Database did not become ready in time.")


def save_access_log(log: dict):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO access_logs (
            event_type,
            ip_address,
            user_agent,
            endpoint,
            http_method,
            status_code,
            request_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            log.get("event_type"),
            log.get("ip_address"),
            log.get("user_agent"),
            log.get("endpoint"),
            log.get("http_method"),
            log.get("status_code"),
            json.dumps(log.get("request_payload", {})),
        ),
    )

    connection.commit()
    cursor.close()
    connection.close()


def save_fraud_alert(log: dict, alert: dict):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO fraud_alerts (
            event_type,
            alert_type,
            severity,
            description,
            ip_address,
            endpoint
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            log.get("event_type"),
            alert.get("alert_type"),
            alert.get("severity"),
            alert.get("description"),
            log.get("ip_address"),
            log.get("endpoint"),
        ),
    )

    connection.commit()
    cursor.close()
    connection.close()
