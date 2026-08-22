from __future__ import annotations
from typing import List, Dict, Any
import random


def run_retry_all_3(transactions: List[Dict[str, Any]], seed: int | None = None) -> Dict[str, Any]:
    """Simulate baseline strategy: retry all eligible transactions up to 3 times."""
    rng = random.Random(seed)
    RAR = 0
    RR = 0
    total_retries = 0
    unnecessary_retries = 0
    recovered_count = 0

    for tx in transactions:
        if tx.get("status") != "failed":
            continue
        RAR += tx.get("amount", 0)
        gt_recoverable = bool(tx.get("_ground_truth_recoverable", False))
        gt_prob = float(tx.get("_ground_truth_recovery_probability", 0.0))
        # skip permanently blocked
        if tx.get("error_code") in {"fraud_detected", "account_closed", "card_stolen"}:
            continue
        for attempt in range(3):
            total_retries += 1
            if not gt_recoverable:
                unnecessary_retries += 1
            outcome = rng.random() < gt_prob
            if outcome and gt_recoverable:
                RR += tx.get("amount", 0)
                recovered_count += 1
                break

    recovery_rate = (RR / RAR) * 100 if RAR > 0 else 0.0
    return {
        "RAR": RAR,
        "RR": RR,
        "recovery_rate": recovery_rate,
        "total_retries": total_retries,
        "unnecessary_retries": unnecessary_retries,
        "recovered_count": recovered_count,
    }
