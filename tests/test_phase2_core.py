import datetime

from services.policy_engine import PolicyEngine
from services.scoring_engine import ScoringEngine
from agent.state_machine import StateMachine
from agent.orchestrator import Orchestrator


def test_policy_engine_basic():
    pe = PolicyEngine()
    tx = {"total_recovery_attempts": 0, "last_recovery_at": None, "amount": 1000, "error_code": "GATEWAY_ERROR"}
    res = pe.validate("retry", tx)
    assert res["approved"] is True


def test_policy_engine_block_permanent():
    pe = PolicyEngine()
    tx = {"total_recovery_attempts": 0, "last_recovery_at": None, "amount": 1000, "error_code": "fraud_detected"}
    res = pe.validate("retry", tx)
    assert res["approved"] is False
    assert res["checks"]["non_permanent"] is False


def test_scoring_engine_ros():
    se = ScoringEngine()
    tx = {"error_code": "GATEWAY_ERROR", "amount": 4999, "created_at": datetime.datetime.utcnow().isoformat(), "total_recovery_attempts": 0}
    customer = {"success_rate": 0.8, "history_score": 0.7}
    out = se.score(tx, customer)
    assert 0.0 <= out["ros"] <= 1.0


def test_state_machine_transitions():
    sm = StateMachine()
    sm.step("detect")
    assert sm.state == "DETECTED"
    sm.step("diagnose")
    assert sm.state == "DIAGNOSING"
    sm.step("done")
    assert sm.state == "DIAGNOSED"


def test_orchestrator_flow():
    orch = Orchestrator()
    tx = {"transaction_id": "txn_test_1", "error_code": "GATEWAY_ERROR", "amount": 1000, "_ground_truth_recoverable": True, "_ground_truth_recovery_probability": 0.9, "created_at": datetime.datetime.utcnow().isoformat(), "total_recovery_attempts": 0}
    customer = {"success_rate": 0.5, "history_score": 0.5}
    out = orch.process(tx, customer)
    assert out["transaction_id"] == "txn_test_1"
    assert "validation" in out
