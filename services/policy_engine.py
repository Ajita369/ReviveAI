from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict


class PolicyEngine:
    MAX_RETRIES = 3
    MIN_COOLDOWN_HOURS = 4
    MAX_AMOUNT_PAISE = 5000000  # ₹50,000
    HUMAN_APPROVAL_THRESHOLD_PAISE = 2500000  # ₹25,000
    PERMANENT_FAILURES = {"fraud_detected", "account_closed", "card_stolen"}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _check_cooldown(self, last_recovery_at: Any) -> bool:
        if not last_recovery_at:
            return True
        # accept either datetime or ISO string
        if isinstance(last_recovery_at, str):
            try:
                last_recovery_at = datetime.fromisoformat(last_recovery_at)
            except Exception:
                return False
        if not isinstance(last_recovery_at, datetime):
            return False
        if last_recovery_at.tzinfo is None:
            last_recovery_at = last_recovery_at.replace(tzinfo=timezone.utc)
        elapsed = self._now() - last_recovery_at
        return elapsed >= timedelta(hours=self.MIN_COOLDOWN_HOURS)

    def validate(self, action: str, tx: Dict[str, Any]) -> Dict[str, Any]:
        checks = {
            "max_retries": tx.get("total_recovery_attempts", 0) < self.MAX_RETRIES,
            "cooldown": self._check_cooldown(tx.get("last_recovery_at")),
            "amount_cap": tx.get("amount", 0) <= self.MAX_AMOUNT_PAISE,
            "non_permanent": tx.get("error_code") not in self.PERMANENT_FAILURES,
            "valid_action": action in {"retry", "payment_link", "reminder", "escalate", "no_action"},
        }
        approved = all(checks.values())
        # add human approval required flag
        human_approval_required = tx.get("amount", 0) > self.HUMAN_APPROVAL_THRESHOLD_PAISE
        return {
            "approved": approved,
            "checks": checks,
            "human_approval_required": human_approval_required,
        }
