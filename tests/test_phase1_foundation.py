from pathlib import Path

from backend.database import get_connection, seed_database, table_counts
from data.generator import (
    AT_RISK_COUNT,
    CUSTOMER_COUNT,
    TARGET_AT_RISK_AMOUNT_PAISE,
    TRANSACTION_COUNT,
    generate_dataset,
    validate_dataset,
)


def test_synthetic_dataset_matches_phase1_plan() -> None:
    dataset = generate_dataset(seed=42)
    summary = validate_dataset(dataset)

    assert summary["customers"] == CUSTOMER_COUNT
    assert summary["transactions"] == TRANSACTION_COUNT
    assert summary["at_risk"] == AT_RISK_COUNT
    assert summary["revenue_at_risk_paise"] == TARGET_AT_RISK_AMOUNT_PAISE


def test_database_schema_and_seed_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "reviveai.db"
    dataset = generate_dataset(seed=42)
    seed_database(dataset.customers, dataset.transactions, db_path=db_path)

    counts = table_counts(db_path)
    assert counts["customers"] == 200
    assert counts["transactions"] == 1000

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM transactions
            GROUP BY status
            """
        ).fetchall()
        status_counts = {row["status"]: row["count"] for row in rows}

        at_risk_total = connection.execute(
            """
            SELECT SUM(amount)
            FROM transactions
            WHERE status IN ('failed', 'abandoned')
            """
        ).fetchone()[0]

    assert status_counts["success"] == 600
    assert status_counts["failed"] + status_counts["abandoned"] == 400
    assert at_risk_total == TARGET_AT_RISK_AMOUNT_PAISE
