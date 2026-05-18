import os
import time
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from app.auth import hash_password

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fraud_user:fraud_password@localhost:5432/fraud_logs_db",
)


@contextmanager
def db_cursor():
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def wait_for_database(max_attempts=30, delay_seconds=2):
    for attempt in range(1, max_attempts + 1):
        try:
            with db_cursor() as cursor:
                cursor.execute("SELECT 1")
            return
        except psycopg2.OperationalError as error:
            print(f"Waiting for database ({attempt}/{max_attempts}): {error}", flush=True)
            time.sleep(delay_seconds)

    raise RuntimeError("Database did not become ready in time.")


def initialize_database():
    wait_for_database()

    with db_cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL,
                revoked BOOLEAN DEFAULT FALSE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin123")

        cursor.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
        if cursor.fetchone() is None:
            cursor.execute(
                """
                INSERT INTO users (email, password_hash, role, two_factor_enabled)
                VALUES (%s, %s, %s, %s)
                """,
                (admin_email, hash_password(admin_password), "admin", False),
            )
