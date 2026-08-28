"""Deterministic synthetic dataset generator for ReviveAI Phase 1."""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import DEFAULT_DB_PATH, reset_database, seed_database, table_counts
from backend.models import (
    Customer,
    CustomerTier,
    DatasetSplit,
    RecoveryStatus,
    Transaction,
    TransactionStatus,
)
from data.ground_truth import FAILURE_MIX, FAILURE_PROFILES


CUSTOMER_COUNT = 200
TRANSACTION_COUNT = 1000
SUCCESSFUL_COUNT = 600
AT_RISK_COUNT = 400
DEV_COUNT = 300
TARGET_AT_RISK_AMOUNT_PAISE = 58_000_000
DEFAULT_SEED = 42
BASE_TIME = datetime(2026, 8, 21, 9, 0, tzinfo=timezone.utc)


FIRST_NAMES = (
    "Aarav",
    "Aditi",
    "Ananya",
    "Arjun",
    "Diya",
    "Ishaan",
    "Kabir",
    "Meera",
    "Neha",
    "Priya",
    "Rahul",
    "Rohan",
    "Sana",
    "Vihaan",
    "Zara",
)
LAST_NAMES = (
    "Iyer",
    "Kapoor",
    "Khan",
    "Mehta",
    "Nair",
    "Patel",
    "Rao",
    "Reddy",
    "Shah",
    "Sharma",
    "Singh",
    "Verma",
)
PAYMENT_METHODS = ("card", "upi", "netbanking", "wallet")


@dataclass(frozen=True, slots=True)
class SyntheticDataset:
    customers: list[Customer]
    transactions: list[Transaction]


def generate_dataset(seed: int = DEFAULT_SEED) -> SyntheticDataset:
    rng = random.Random(seed)
    customers = _generate_customers(rng)
    at_risk_amounts = _amounts_with_target_total(rng, AT_RISK_COUNT)

    transactions: list[Transaction] = []
    for index in range(TRANSACTION_COUNT):
        transaction_number = index + 1
        customer = customers[index % CUSTOMER_COUNT]
        split = DatasetSplit.DEV if index < DEV_COUNT else DatasetSplit.TEST
        created_at = BASE_TIME - timedelta(hours=rng.randint(1, 24 * 30))

        if index < SUCCESSFUL_COUNT:
            transactions.append(
                Transaction(
                    transaction_id=f"txn_{transaction_number:04d}",
                    order_id=f"order_{transaction_number:04d}",
                    customer_id=customer.customer_id,
                    amount=_round_to_paise(rng.randint(29900, 249900)),
                    currency="INR",
                    status=TransactionStatus.SUCCESS,
                    payment_method=rng.choice(PAYMENT_METHODS),
                    created_at=created_at,
                    dataset_split=split,
                    recovery_status=RecoveryStatus.NOT_REQUIRED,
                    gt_recoverable=False,
                    gt_recovery_probability=0.0,
                    gt_recommended_action="no_action",
                )
            )
            continue

        error_code = _weighted_failure_code(rng)
        profile = FAILURE_PROFILES[error_code]
        amount = at_risk_amounts[index - SUCCESSFUL_COUNT]
        probability = float(profile["recoverable_probability"])
        recoverable = probability > 0 and rng.random() < min(0.95, probability + 0.15)
        status = TransactionStatus.ABANDONED if error_code is None else TransactionStatus.FAILED
        transactions.append(
            Transaction(
                transaction_id=f"txn_{transaction_number:04d}",
                order_id=f"order_{transaction_number:04d}",
                customer_id=customer.customer_id,
                amount=amount,
                currency="INR",
                status=status,
                payment_method=str(profile["payment_method"]),
                failure_reason=str(profile["failure_reason"]),
                error_code=error_code,
                error_description=str(profile["description"]),
                created_at=created_at,
                dataset_split=split,
                recovery_status=RecoveryStatus.NEW,
                gt_recoverable=recoverable,
                gt_recovery_probability=probability if recoverable else 0.0,
                gt_recommended_action=str(profile["recommended_action"]),
            )
        )

    rng.shuffle(transactions)
    transactions = _assign_stable_splits(transactions)
    return SyntheticDataset(customers=customers, transactions=transactions)


def generate_and_seed(
    db_path: str | Path = DEFAULT_DB_PATH,
    seed: int = DEFAULT_SEED,
    reset: bool = True,
) -> dict[str, int]:
    dataset = generate_dataset(seed=seed)
    if reset:
        reset_database(db_path)
    seed_database(dataset.customers, dataset.transactions, db_path=db_path)
    return table_counts(db_path)


def validate_dataset(dataset: SyntheticDataset) -> dict[str, int | float]:
    transactions = dataset.transactions
    at_risk = [
        tx for tx in transactions if tx.status in {TransactionStatus.FAILED, TransactionStatus.ABANDONED}
    ]
    successful = [tx for tx in transactions if tx.status == TransactionStatus.SUCCESS]
    recoverable = [tx for tx in at_risk if tx.gt_recoverable]
    dev = [tx for tx in transactions if tx.dataset_split == DatasetSplit.DEV]
    test = [tx for tx in transactions if tx.dataset_split == DatasetSplit.TEST]

    assert len(dataset.customers) == CUSTOMER_COUNT
    assert len(transactions) == TRANSACTION_COUNT
    assert len(successful) == SUCCESSFUL_COUNT
    assert len(at_risk) == AT_RISK_COUNT
    assert len(dev) == DEV_COUNT
    assert len(test) == TRANSACTION_COUNT - DEV_COUNT
    assert sum(tx.amount for tx in at_risk) == TARGET_AT_RISK_AMOUNT_PAISE
    assert all(tx.currency == "INR" for tx in transactions)
    assert all(tx.gt_recovery_probability is not None for tx in transactions)

    return {
        "customers": len(dataset.customers),
        "transactions": len(transactions),
        "successful": len(successful),
        "at_risk": len(at_risk),
        "recoverable_at_risk": len(recoverable),
        "dev": len(dev),
        "test": len(test),
        "revenue_at_risk_paise": sum(tx.amount for tx in at_risk),
        "avg_recovery_probability": round(
            sum(float(tx.gt_recovery_probability or 0) for tx in at_risk) / len(at_risk), 4
        ),
    }


def _generate_customers(rng: random.Random) -> list[Customer]:
    customers: list[Customer] = []
    for index in range(1, CUSTOMER_COUNT + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        tier = rng.choices(
            list(CustomerTier),
            weights=(0.45, 0.28, 0.20, 0.07),
            k=1,
        )[0]
        tier_bonus = {
            CustomerTier.STANDARD: 0.00,
            CustomerTier.SILVER: 0.05,
            CustomerTier.GOLD: 0.10,
            CustomerTier.PLATINUM: 0.15,
        }[tier]
        success_rate = min(0.99, max(0.45, rng.gauss(0.78 + tier_bonus, 0.10)))
        history_score = min(1.0, max(0.25, rng.gauss(0.70 + tier_bonus, 0.12)))
        total = rng.randint(3, 36)
        failed = min(total, round(total * (1 - success_rate)))
        customers.append(
            Customer(
                customer_id=f"cust_{index:03d}",
                name=f"{first} {last}",
                email=f"{first.lower()}.{last.lower()}{index:03d}@example.com",
                contact=f"+9198{rng.randint(10000000, 99999999)}",
                tier=tier,
                success_rate=round(success_rate, 3),
                history_score=round(history_score, 3),
                total_transactions=total,
                failed_transactions=failed,
                created_at=BASE_TIME - timedelta(days=rng.randint(30, 900)),
            )
        )
    return customers


def _weighted_failure_code(rng: random.Random) -> str | None:
    codes = [code for code, _weight in FAILURE_MIX]
    weights = [weight for _code, weight in FAILURE_MIX]
    return rng.choices(codes, weights=weights, k=1)[0]


def _amounts_with_target_total(rng: random.Random, count: int) -> list[int]:
    raw_amounts = [_round_to_paise(rng.randint(39900, 349900)) for _ in range(count)]
    scale = TARGET_AT_RISK_AMOUNT_PAISE / sum(raw_amounts)
    amounts = [_round_to_paise(max(9900, int(amount * scale))) for amount in raw_amounts]
    delta = TARGET_AT_RISK_AMOUNT_PAISE - sum(amounts)
    step = 100 if delta >= 0 else -100
    for index in range(abs(delta) // 100):
        amounts[index % count] += step
    return amounts


def _round_to_paise(amount: int) -> int:
    return int(round(amount / 100) * 100)


def _assign_stable_splits(transactions: list[Transaction]) -> list[Transaction]:
    ordered = sorted(transactions, key=lambda tx: tx.transaction_id)
    split_by_id = {
        tx.transaction_id: DatasetSplit.DEV if index < DEV_COUNT else DatasetSplit.TEST
        for index, tx in enumerate(ordered)
    }
    return [
        Transaction(
            **{
                **tx.to_record(include_ground_truth=True),
                "status": tx.status,
                "created_at": tx.created_at,
                "dataset_split": split_by_id[tx.transaction_id],
                "recovery_status": tx.recovery_status,
                "recovery_priority": tx.recovery_priority,
                "last_recovery_at": tx.last_recovery_at,
            }
        )
        for tx in transactions
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and seed ReviveAI synthetic data.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Deterministic RNG seed")
    parser.add_argument("--no-reset", action="store_true", help="Do not recreate the database")
    args = parser.parse_args()

    dataset = generate_dataset(seed=args.seed)
    summary = validate_dataset(dataset)
    counts = generate_and_seed(args.db, seed=args.seed, reset=not args.no_reset)
    print({"dataset": summary, "database": counts})


if __name__ == "__main__":
    main()
