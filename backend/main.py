from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from agent.orchestrator import Orchestrator
from backend.database import DEFAULT_DB_PATH, get_connection, initialize_database
from services.llm_service import LLMService
from services.scoring_engine import ScoringEngine


class RecoveryRequest(BaseModel):
    action: str | None = Field(default=None)
    customer: dict[str, Any] | None = None


def _public_row(row: Any) -> dict[str, Any]:
    result = dict(row)
    for key in ("gt_recoverable", "gt_recovery_probability", "gt_recommended_action"):
        result.pop(key, None)
    return result


def _find_transaction(db_path: Path, transaction_id: str) -> dict[str, Any]:
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return dict(row)


def create_app(db_path: str | Path = DEFAULT_DB_PATH) -> FastAPI:
    path = Path(db_path)
    initialize_database(path)
    app = FastAPI(title="ReviveAI API", version="1.0.0")
    orchestrator = Orchestrator()
    llm = LLMService()
    scoring = ScoringEngine()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/transactions")
    def list_transactions(
        status: str | None = None,
        recovery_status: str | None = None,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if recovery_status:
            clauses.append("recovery_status = ?")
            params.append(recovery_status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with get_connection(path) as connection:
            rows = connection.execute(
                f"SELECT * FROM transactions {where} ORDER BY recovery_score DESC NULLS LAST, created_at DESC LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
            total = connection.execute(
                f"SELECT COUNT(*) FROM transactions {where}", params
            ).fetchone()[0]
        return {"items": [_public_row(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    @app.get("/transactions/{transaction_id}")
    def get_transaction(transaction_id: str) -> dict[str, Any]:
        transaction = _find_transaction(path, transaction_id)
        with get_connection(path) as connection:
            attempts = connection.execute(
                "SELECT * FROM recovery_attempts WHERE transaction_id = ? ORDER BY attempt_number",
                (transaction_id,),
            ).fetchall()
            decisions = connection.execute(
                "SELECT * FROM agent_decisions WHERE transaction_id = ? ORDER BY created_at",
                (transaction_id,),
            ).fetchall()
        return {"transaction": _public_row(transaction), "attempts": [dict(row) for row in attempts], "decisions": [dict(row) for row in decisions]}

    @app.post("/analyze/{transaction_id}")
    def analyze_transaction(transaction_id: str) -> dict[str, Any]:
        transaction = _find_transaction(path, transaction_id)
        with get_connection(path) as connection:
            customer_row = connection.execute(
                "SELECT * FROM customers WHERE customer_id = ?", (transaction["customer_id"],)
            ).fetchone()
        customer = dict(customer_row) if customer_row else {"success_rate": 0.5, "history_score": 0.5}
        diagnosis = llm.diagnose_failure(transaction)
        score = scoring.score(transaction, customer)
        action = orchestrator.decide_action(transaction, customer)
        return {"transaction_id": transaction_id, "diagnosis": diagnosis, "score": score, "recommended_action": action}

    @app.post("/recover/{transaction_id}")
    def recover_transaction(transaction_id: str, request: RecoveryRequest | None = None) -> dict[str, Any]:
        transaction = _find_transaction(path, transaction_id)
        request = request or RecoveryRequest()
        with get_connection(path) as connection:
            customer_row = connection.execute(
                "SELECT * FROM customers WHERE customer_id = ?", (transaction["customer_id"],)
            ).fetchone()
        customer = request.customer or (dict(customer_row) if customer_row else {"success_rate": 0.5, "history_score": 0.5})
        action = request.action or orchestrator.decide_action(transaction, customer)
        validation = orchestrator.policy.validate(action, transaction)
        action_id = hashlib.sha256(f"{transaction_id}:{action}:{transaction['total_recovery_attempts']}".encode()).hexdigest()
        now = datetime.now(timezone.utc).isoformat()
        if not validation["approved"]:
            result = {"status": "policy_blocked", "action": action, "validation": validation}
        else:
            attempt_number = transaction["total_recovery_attempts"] + 1
            with get_connection(path) as connection:
                try:
                    connection.execute(
                        "INSERT INTO recovery_attempts (attempt_id, transaction_id, action_id, action_type, attempt_number, status, result, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), transaction_id, action_id, action, attempt_number, "simulated", "queued", now),
                    )
                    connection.execute(
                        "UPDATE transactions SET total_recovery_attempts = ?, last_recovery_at = ?, recovery_status = ? WHERE transaction_id = ?",
                        (attempt_number, now, "retry_scheduled", transaction_id),
                    )
                    connection.execute(
                        "INSERT INTO audit_events (event_id, timestamp, transaction_id, event_type, previous_state, new_state, reason, agent_output, policy_checks, action_selected, result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), now, transaction_id, "recovery_requested", transaction["recovery_status"], "retry_scheduled", "Policy approved recovery action", json.dumps({"action": action}), json.dumps(validation["checks"]), action, "simulated"),
                    )
                except Exception as exc:
                    raise HTTPException(status_code=409, detail=f"Recovery action already exists or failed: {exc}") from exc
            result = {"status": "accepted", "action": action, "attempt_number": attempt_number, "action_id": action_id, "validation": validation}
        return {"transaction_id": transaction_id, **result}

    @app.get("/audit")
    def list_audit(transaction_id: str | None = None, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
        with get_connection(path) as connection:
            if transaction_id:
                rows = connection.execute("SELECT * FROM audit_events WHERE transaction_id = ? ORDER BY timestamp DESC LIMIT ?", (transaction_id, limit)).fetchall()
            else:
                rows = connection.execute("SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return {"items": [dict(row) for row in rows]}

    @app.get("/metrics")
    def metrics() -> dict[str, Any]:
        with get_connection(path) as connection:
            totals = connection.execute("SELECT COUNT(*) AS transactions, COALESCE(SUM(CASE WHEN status IN ('failed', 'abandoned') THEN amount ELSE 0 END), 0) AS revenue_at_risk FROM transactions").fetchone()
            recovered = connection.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE recovery_status = 'recovered'").fetchone()[0]
            status_rows = connection.execute("SELECT recovery_status, COUNT(*) AS count FROM transactions GROUP BY recovery_status").fetchall()
        risk = int(totals["revenue_at_risk"])
        return {"transactions": int(totals["transactions"]), "revenue_at_risk_paise": risk, "revenue_recovered_paise": int(recovered), "recovery_rate": (int(recovered) / risk * 100 if risk else 0.0), "recovery_status_counts": {row["recovery_status"]: row["count"] for row in status_rows}}

    return app


app = create_app(Path(os.getenv("REVIVEAI_DB_PATH", str(DEFAULT_DB_PATH))))
