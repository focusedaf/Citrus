import os
import json
import time
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
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
    conn.commit()
    cur.close()
    conn.close()


def save_trace(address, chain_id, summary, edges, risk):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO traces (address, chain_id, created_at, risk_score, risk_level, summary_json, edges_json)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (
            address, chain_id, int(time.time()),
            risk.get("score", 0), risk.get("level", "Low"),
            psycopg2.extras.Json(summary), psycopg2.extras.Json(edges),
        ),
    )
    trace_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return trace_id


def save_complaint(address, source="NCRP/SAHYOG (mock)", trace_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO complaints (address, source, received_at, trace_id) VALUES (%s, %s, %s, %s)",
        (address, source, int(time.time()), trace_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def save_alert(trace_id, address, risk_level, message):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO alerts (trace_id, address, risk_level, message, created_at) VALUES (%s, %s, %s, %s, %s)",
        (trace_id, address, risk_level, message, int(time.time())),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_all_traces(limit=50):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM traces ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]


def get_trace_by_id(trace_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM traces WHERE id = %s", (trace_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_all_alerts(limit=50):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]