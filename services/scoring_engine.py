from __future__ import annotations
from datetime import datetime
from typing import Dict, Any


FAILURE_RECOVERABILITY = {
    "GATEWAY_ERROR": 0.85,
    "insufficient_balance": 0.4,
    "card_expired": 0.35,
    "authentication_failed": 0.7,
    "bank_declined": 0.3,
    "fraud_detected": 0.0,
}


class ScoringEngine:
    """Computes Recovery Opportunity Score (ROS) as specified in the plan."""

    def _hours_since(self, created_at: Any) -> float:
        if not created_at:
            return 0.0
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except Exception:
                return 0.0
        if not isinstance(created_at, datetime):
            return 0.0
        delta = datetime.utcnow() - created_at
        return delta.total_seconds() / 3600.0

    def score(self, tx: Dict[str, Any], customer: Dict[str, Any]) -> Dict[str, Any]:
        # F: failure recoverability
        error = tx.get("error_code", "")
        F = FAILURE_RECOVERABILITY.get(error, 0.3)

        # C: customer reliability (success_rate * 0.6 + history_score * 0.4)
        success_rate = float(customer.get("success_rate", 0.0))
        history_score = float(customer.get("history_score", 0.5))
        C = success_rate * 0.6 + history_score * 0.4

        # A: amount factor - amount is expected in paise; convert to rupees
        amount_paise = tx.get("amount", 0)
        amount_rs = amount_paise / 100.0
        A = min(amount_rs / 10000.0, 1.0)

        # T: time decay
        hours = self._hours_since(tx.get("created_at"))
        T = max(0.0, 1.0 - hours / 168.0)

        # P: attempt penalty = previous_attempts * 0.3
        prev_attempts = int(tx.get("total_recovery_attempts", 0))
        P = prev_attempts * 0.3

        ros = 0.35 * F + 0.25 * C + 0.15 * A + 0.15 * T - 0.10 * P
        # clamp
        ros = max(0.0, min(1.0, ros))

        tier = "SKIP"
        if ros >= 0.7:
            tier = "HIGH"
        elif ros >= 0.4:
            tier = "MEDIUM"
        elif ros >= 0.2:
            tier = "LOW"

        return {"ros": ros, "tier": tier, "components": {"F": F, "C": C, "A": A, "T": T, "P": P}}
