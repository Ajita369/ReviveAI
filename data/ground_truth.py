"""Ground-truth probabilities for the synthetic recovery dataset."""

from __future__ import annotations

FAILURE_PROFILES: dict[str | None, dict[str, object]] = {
    "GATEWAY_ERROR": {
        "failure_reason": "Gateway Timeout",
        "description": "Processing timeout at issuing bank",
        "recoverable_probability": 0.85,
        "recommended_action": "retry",
        "payment_method": "card",
    },
    "insufficient_balance": {
        "failure_reason": "Insufficient Funds",
        "description": "Customer bank reported insufficient balance",
        "recoverable_probability": 0.40,
        "recommended_action": "payment_link",
        "payment_method": "upi",
    },
    "card_expired": {
        "failure_reason": "Card Expired",
        "description": "Card expiry date is no longer valid",
        "recoverable_probability": 0.35,
        "recommended_action": "payment_link",
        "payment_method": "card",
    },
    "authentication_failed": {
        "failure_reason": "Authentication Failed",
        "description": "Customer did not complete OTP or 3DS challenge",
        "recoverable_probability": 0.70,
        "recommended_action": "retry",
        "payment_method": "card",
    },
    "bank_declined": {
        "failure_reason": "Bank Declined",
        "description": "Issuer declined the transaction",
        "recoverable_probability": 0.30,
        "recommended_action": "retry",
        "payment_method": "card",
    },
    "fraud_detected": {
        "failure_reason": "Fraud Suspected",
        "description": "Payment was blocked by fraud-risk checks",
        "recoverable_probability": 0.00,
        "recommended_action": "no_action",
        "payment_method": "card",
    },
    None: {
        "failure_reason": "Abandoned Checkout",
        "description": "Customer dropped off before completing payment",
        "recoverable_probability": 0.50,
        "recommended_action": "payment_link",
        "payment_method": "upi",
    },
}

FAILURE_MIX: tuple[tuple[str | None, float], ...] = (
    ("GATEWAY_ERROR", 0.24),
    ("insufficient_balance", 0.22),
    ("card_expired", 0.12),
    ("authentication_failed", 0.18),
    ("bank_declined", 0.12),
    ("fraud_detected", 0.05),
    (None, 0.07),
)

PERMANENT_FAILURES = {"fraud_detected", "account_closed", "card_stolen"}
