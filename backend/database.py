"""SQLite setup and persistence helpers for the ReviveAI foundation."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from backend.models import Customer, Transaction


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "reviveai.db"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    contact TEXT NOT NULL,
    tier TEXT NOT NULL,
    success_rate REAL NOT NULL CHECK(success_rate >= 0 AND success_rate <= 1),
    history_score REAL NOT NULL CHECK(history_score >= 0 AND history_score <= 1),
    total_transactions INTEGER NOT NULL CHECK(total_transactions >= 0),
    failed_transactions INTEGER NOT NULL CHECK(failed_transactions >= 0),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK(amount > 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'abandoned')),
    payment_method TEXT NOT NULL,
    failure_reason TEXT,
    error_code TEXT,
    error_description TEXT,
    recovery_status TEXT NOT NULL DEFAULT 'new',
    recovery_priority TEXT,
    recovery_score REAL,
    total_recovery_attempts INTEGER NOT NULL DEFAULT 0 CHECK(total_recovery_attempts >= 0),
    last_recovery_at TEXT,
    gt_recoverable INTEGER,
    gt_recovery_probability REAL CHECK(gt_recovery_probability IS NULL OR (gt_recovery_probability >= 0 AND gt_recovery_probability <= 1)),
    gt_recommended_action TEXT,
    dataset_split TEXT NOT NULL CHECK(dataset_split IN ('dev', 'test')),
    created_at TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS recovery_attempts (
    attempt_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    action_id TEXT NOT NULL UNIQUE,
    action_type TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK(attempt_number > 0),
    status TEXT NOT NULL,
    payment_link_id TEXT,
    payment_link_url TEXT,
    result TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id)
);

CREATE TABLE IF NOT EXISTS agent_decisions (
    decision_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    state TEXT NOT NULL,
    diagnosis TEXT,
    recovery_score REAL,
    recovery_priority TEXT,
    action_selected TEXT,
    rationale TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    reason TEXT,
    agent_output TEXT,
    policy_checks TEXT,
    action_selected TEXT,
    result TEXT,
    FOREIGN KEY(transaction_id) REFERENCES transactions(transaction_id)
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    dimensions TEXT,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_recovery_status ON transactions(recovery_status);
CREATE INDEX IF NOT EXISTS idx_transactions_split ON transactions(dataset_split);
CREATE INDEX IF NOT EXISTS idx_audit_events_transaction ON audit_events(transaction_id);
"""


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    with get_connection(path) as connection:
        connection.executescript(SCHEMA_SQL)
    return path


def reset_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    if path.exists():
        path.unlink()
    return initialize_database(path)


def seed_database(
    customers: Iterable[Customer],
    transactions: Iterable[Transaction],
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Path:
    path = initialize_database(db_path)
    customer_records = [customer.to_record() for customer in customers]
    transaction_records = [transaction.to_record() for transaction in transactions]

    with get_connection(path) as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO customers (
                customer_id, name, email, contact, tier, success_rate, history_score,
                total_transactions, failed_transactions, created_at
            ) VALUES (
                :customer_id, :name, :email, :contact, :tier, :success_rate,
                :history_score, :total_transactions, :failed_transactions, :created_at
            )
            """,
            customer_records,
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO transactions (
                transaction_id, order_id, customer_id, amount, currency, status,
                payment_method, failure_reason, error_code, error_description,
                recovery_status, recovery_priority, recovery_score,
                total_recovery_attempts, last_recovery_at, gt_recoverable,
                gt_recovery_probability, gt_recommended_action, dataset_split, created_at
            ) VALUES (
                :transaction_id, :order_id, :customer_id, :amount, :currency, :status,
                :payment_method, :failure_reason, :error_code, :error_description,
                :recovery_status, :recovery_priority, :recovery_score,
                :total_recovery_attempts, :last_recovery_at, :gt_recoverable,
                :gt_recovery_probability, :gt_recommended_action, :dataset_split, :created_at
            )
            """,
            [_sqlite_record(record) for record in transaction_records],
        )
    return path


def table_counts(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, int]:
    tables = (
        "customers",
        "transactions",
        "recovery_attempts",
        "agent_decisions",
        "audit_events",
        "metrics",
    )
    with get_connection(db_path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def _sqlite_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: int(value) if isinstance(value, bool) else value
        for key, value in record.items()
    }
