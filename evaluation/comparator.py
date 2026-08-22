from __future__ import annotations
from typing import Dict, Any


def compare(baseline: Dict[str, Any], revive: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "baseline": baseline,
        "revive": revive,
        "delta_recovered": revive.get("recovered", 0) - baseline.get("recovered", 0),
        "delta_amount": revive.get("recovered_amount", 0) - baseline.get("recovered_amount", 0),
    }
