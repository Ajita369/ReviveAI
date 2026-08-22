from __future__ import annotations
from typing import Dict, Any, List
from time import time
import uuid


class FakeRazorpayClient:
    """A tiny in-memory simulator for Razorpay Test Mode payment links."""

    def __init__(self) -> None:
        self._links: List[Dict[str, Any]] = []

    def payment_link_create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        lid = f"plink_{uuid.uuid4().hex[:12]}"
        now = int(time())
        link = {
            "id": lid,
            "short_url": f"https://rzp.test/{lid}",
            "amount": payload.get("amount"),
            "currency": payload.get("currency", "INR"),
            "description": payload.get("description"),
            "customer": payload.get("customer", {}),
            "notify": payload.get("notify", {}),
            "expire_by": payload.get("expire_by", now + 3600 * 24),
            "status": "created",
            "created_at": now,
        }
        self._links.append(link)
        return link

    def payment_link_get(self, link_id: str) -> Dict[str, Any] | None:
        for l in self._links:
            if l["id"] == link_id:
                return l
        return None
