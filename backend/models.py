"""Typed domain models used by the ReviveAI foundation layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class TransactionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    ABANDONED = "abandoned"


class RecoveryStatus(StrEnum):
    NEW = "new"
    NOT_REQUIRED = "not_required"
    DETECTED = "detected"
    SCORED = "scored"
    RECOVERED = "recovered"
    RETRY_SCHEDULED = "retry_scheduled"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"


class RecoveryPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SKIP = "skip"


class CustomerTier(StrEnum):
    STANDARD = "standard"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class DatasetSplit(StrEnum):
    DEV = "dev"
    TEST = "test"


@dataclass(frozen=True, slots=True)
class Customer:
    customer_id: str
    name: str
    email: str
    contact: str
    tier: CustomerTier
    success_rate: float
    history_score: float
    total_transactions: int
    failed_transactions: int
    created_at: datetime

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["tier"] = self.tier.value
        record["created_at"] = to_iso(self.created_at)
        return record


@dataclass(frozen=True, slots=True)
class Transaction:
    transaction_id: str
    order_id: str
    customer_id: str
    amount: int
    currency: str
    status: TransactionStatus
    payment_method: str
    created_at: datetime
    dataset_split: DatasetSplit
    failure_reason: str | None = None
    error_code: str | None = None
    error_description: str | None = None
    recovery_status: RecoveryStatus = RecoveryStatus.NEW
    recovery_priority: RecoveryPriority | None = None
    recovery_score: float | None = None
    total_recovery_attempts: int = 0
    last_recovery_at: datetime | None = None
    gt_recoverable: bool | None = None
    gt_recovery_probability: float | None = None
    gt_recommended_action: str | None = None

    def to_record(self, include_ground_truth: bool = True) -> dict[str, Any]:
        record = asdict(self)
        record["status"] = self.status.value
        record["created_at"] = to_iso(self.created_at)
        record["dataset_split"] = self.dataset_split.value
        record["recovery_status"] = self.recovery_status.value
        record["recovery_priority"] = (
            self.recovery_priority.value if self.recovery_priority else None
        )
        record["last_recovery_at"] = (
            to_iso(self.last_recovery_at) if self.last_recovery_at else None
        )
        if not include_ground_truth:
            for key in (
                "gt_recoverable",
                "gt_recovery_probability",
                "gt_recommended_action",
            ):
                record.pop(key, None)
        return record


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    timestamp: datetime
    transaction_id: str
    event_type: str
    previous_state: str | None = None
    new_state: str | None = None
    reason: str | None = None
    agent_output: str | None = None
    policy_checks: str | None = None
    action_selected: str | None = None
    result: str | None = None

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["timestamp"] = to_iso(self.timestamp)
        return record


def to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
