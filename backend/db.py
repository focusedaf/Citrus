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

            # --- Migrations for existing databases -------------------------
            # ADD COLUMN IF NOT EXISTS is safe to re-run and never touches
            # existing rows/columns, so this won't break a DB you already
            # have data in.
            cur.execute("""
                ALTER TABLE traces
                ADD COLUMN IF NOT EXISTS evidence_hash TEXT
            """)

            cur.execute("ALTER TABLE traces ADD COLUMN IF NOT EXISTS tags_json JSONB")
            cur.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acknowledged BOOLEAN NOT NULL DEFAULT FALSE")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    trace_id INTEGER NOT NULL UNIQUE REFERENCES traces(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    complaint_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    victim_state TEXT NOT NULL DEFAULT '—',
                    chain TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'New',
                    amount_inr NUMERIC NOT NULL DEFAULT 0,
                    created_at BIGINT NOT NULL,
                    lead TEXT NOT NULL DEFAULT 'm1'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workspace_members (
                    workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,
                    member_id TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, member_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workspace_comments (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,
                    by_member TEXT NOT NULL,
                    text TEXT NOT NULL,
                    at BIGINT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workspace_tasks (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    assignee TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at BIGINT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workspace_activity (
                    id BIGSERIAL PRIMARY KEY,
                    workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,
                    by_member TEXT NOT NULL,
                    text TEXT NOT NULL,
                    at BIGINT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workspace_nodes (
                    workspace_id TEXT REFERENCES workspaces(id) ON DELETE CASCADE,
                    address TEXT NOT NULL,
                    flagged BOOLEAN NOT NULL DEFAULT FALSE,
                    notes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    PRIMARY KEY (workspace_id, address)
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


def save_trace(address, chain_id, summary, edges, risk, evidence_hash=None, tags=None,  max_hops=None):
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
                    edges_json,
                    evidence_hash,
                    tags_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    evidence_hash,
                    psycopg2.extras.Json(tags or {}),
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