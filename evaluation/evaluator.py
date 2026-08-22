from __future__ import annotations
from typing import List, Dict, Any
import random


def _is_permanent(error_code: str | None) -> bool:
    return error_code in {"fraud_detected", "account_closed", "card_stolen"}


def _correct_action_for_error(error_code: str | None) -> str:
    mapping = {
        "GATEWAY_ERROR": "retry",
        "insufficient_balance": "payment_link",
        "card_expired": "payment_link",
        "authentication_failed": "retry",
        "bank_declined": "retry",
        "fraud_detected": "no_action",
    }
    return mapping.get(error_code, "retry")


def run_reviveai(orchestrator, transactions: List[Dict[str, Any]], customers: Dict[str, Dict[str, Any]], seed: int | None = None) -> Dict[str, Any]:
    rng = random.Random(seed)
    RAR = 0
    RR = 0
    total_attempts = 0
    unnecessary_retries = 0
    policy_violations = 0
    recovered_count = 0

    for tx in transactions:
        if tx.get("status") != "failed":
            continue
        RAR += tx.get("amount", 0)
        cid = tx.get("customer_id")
        customer = customers.get(cid, {"success_rate": 0.5, "history_score": 0.5})
        attempts = 0
        max_retries = orchestrator.policy.MAX_RETRIES
        # skip permanent failures
        if _is_permanent(tx.get("error_code")):
            continue
        recovered = False
        while attempts < max_retries and not recovered:
            action = orchestrator.decide_action(tx, customer)
            validation = orchestrator.policy.validate(action, tx)
            if not validation.get("approved"):
                policy_violations += 1
                break
            # simulate attempt
            attempts += 1
            total_attempts += 1
            correct = (_correct_action_for_error(tx.get("error_code")) == action)
            gt_recoverable = bool(tx.get("_ground_truth_recoverable", False))
            gt_prob = float(tx.get("_ground_truth_recovery_probability", 0.0))
            if not gt_recoverable:
                unnecessary_retries += 1
            prob = gt_prob if correct else gt_prob * 0.5
            outcome = rng.random() < prob
            if outcome and gt_recoverable:
                RR += tx.get("amount", 0)
                recovered = True
                recovered_count += 1
                break

        # record attempts count in tx for reporting
        tx["sim_attempts"] = attempts

    recovery_rate = (RR / RAR) * 100 if RAR > 0 else 0.0
    return {
        "RAR": RAR,
        "RR": RR,
        "recovery_rate": recovery_rate,
        "total_attempts": total_attempts,
        "unnecessary_retries": unnecessary_retries,
        "policy_violations": policy_violations,
        "recovered_count": recovered_count,
    }
