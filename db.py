import os
import time
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to your .env file, e.g.\n"
        "DATABASE_URL=postgresql://user:password@host:5432/dbname"
    )


@contextmanager
def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def _reset_sequence_if_empty(cur, table_name, sequence_name):
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute(
            f"ALTER SEQUENCE {sequence_name} RESTART WITH 1"
        )


def init_db():
    with get_connection() as conn:
        cur = conn.cursor()

        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id SERIAL PRIMARY KEY,
                    address TEXT NOT NULL,
                    chain_id INTEGER NOT NULL,
                    created_at BIGINT NOT NULL,
                    risk_score INTEGER,
                    risk_level TEXT,
                    summary_json JSONB,
                    edges_json JSONB
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS complaints (
                    id SERIAL PRIMARY KEY,
                    address TEXT NOT NULL,
                    source TEXT NOT NULL,
                    received_at BIGINT NOT NULL,
                    trace_id INTEGER REFERENCES traces(id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    trace_id INTEGER REFERENCES traces(id),
                    address TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at BIGINT NOT NULL
                )
            """)

            _reset_sequence_if_empty(
                cur,
                "traces",
                "traces_id_seq"
            )

            _reset_sequence_if_empty(
                cur,
                "complaints",
                "complaints_id_seq"
            )

            _reset_sequence_if_empty(
                cur,
                "alerts",
                "alerts_id_seq"
            )

            conn.commit()

        finally:
            cur.close()


def save_trace(address, chain_id, summary, edges, risk):
    with get_connection() as conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO traces (
                    address,
                    chain_id,
                    created_at,
                    risk_score,
                    risk_level,
                    summary_json,
                    edges_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    address,
                    chain_id,
                    int(time.time()),
                    risk.get("score", 0),
                    risk.get("level", "Low"),
                    psycopg2.extras.Json(summary),
                    psycopg2.extras.Json(edges),
                ),
            )

            trace_id = cur.fetchone()[0]
            conn.commit()

            return trace_id

        finally:
            cur.close()


def save_complaint(
    address,
    source="NCRP/SAHYOG (mock)",
    trace_id=None
):
    with get_connection() as conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO complaints (
                    address,
                    source,
                    received_at,
                    trace_id
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    address,
                    source,
                    int(time.time()),
                    trace_id,
                ),
            )

            conn.commit()

        finally:
            cur.close()


def save_alert(trace_id, address, risk_level, message):
    with get_connection() as conn:
        cur = conn.cursor()

        try:
            cur.execute(
                """
                INSERT INTO alerts (
                    trace_id,
                    address,
                    risk_level,
                    message,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    trace_id,
                    address,
                    risk_level,
                    message,
                    int(time.time()),
                ),
            )

            conn.commit()

        finally:
            cur.close()


def get_all_traces(limit=50):
    with get_connection() as conn:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        try:
            cur.execute(
                """
                SELECT *
                FROM traces
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )

            rows = cur.fetchall()
            return [dict(row) for row in rows]

        finally:
            cur.close()


def get_trace_by_id(trace_id):
    with get_connection() as conn:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        try:
            cur.execute(
                "SELECT * FROM traces WHERE id = %s",
                (trace_id,),
            )

            row = cur.fetchone()
            return dict(row) if row else None

        finally:
            cur.close()


def get_all_alerts(limit=50):
    with get_connection() as conn:
        cur = conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        try:
            cur.execute(
                """
                SELECT *
                FROM alerts
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )

            rows = cur.fetchall()
            return [dict(row) for row in rows]

        finally:
            cur.close()