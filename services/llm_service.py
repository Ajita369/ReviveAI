from __future__ import annotations
from typing import Dict, Any


ERROR_LOOKUP = {
    "GATEWAY_ERROR": "Gateway timeout / temporary network issue at issuer bank.",
    "insufficient_balance": "Insufficient funds in customer's account.",
    "card_expired": "Card expired; customer needs to update payment method.",
    "authentication_failed": "Authentication (3DS/OTP) failed or was dropped.",
    "bank_declined": "Issuer declined the transaction; could be temporary or permanent.",
    "fraud_detected": "Transaction flagged as possible fraud; do not retry.",
}


class LLMService:
    """Simple LLM service with deterministic fallback mapping.

    This implementation is intentionally lightweight for offline/hackathon
    usage: it does not call external APIs but returns a deterministic
    diagnosis based on known error codes.
    """

    def diagnose_failure(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        code = tx.get("error_code")
        reason = ERROR_LOOKUP.get(code)
        if reason:
            recoverable = code != "fraud_detected"
            confidence = 0.9
        else:
            reason = tx.get("error_description") or "Unknown failure"
            recoverable = True
            confidence = 0.5
        return {"error_code": code, "diagnosis": reason, "recoverable": recoverable, "confidence": confidence}
