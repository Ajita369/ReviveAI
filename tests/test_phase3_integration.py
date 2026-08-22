import random
from agent.orchestrator import Orchestrator
from services.llm_service import LLMService
from services.razorpay_client import FakeRazorpayClient
from evaluation.baseline import run_retry_all_3
from evaluation.evaluator import run_reviveai


def _make_customers(n=10):
    customers = {}
    for i in range(n):
        customers[f"cust_{i}"] = {"success_rate": random.random(), "history_score": random.random()}
    return customers


def _make_transactions(customers, n=50, seed=1):
    random.seed(seed)
    error_codes = ["GATEWAY_ERROR", "insufficient_balance", "card_expired", "authentication_failed", "bank_declined", "fraud_detected"]
    txs = []
    for i in range(n):
        cid = random.choice(list(customers.keys()))
        code = random.choice(error_codes)
        gt_recoverable = code != "fraud_detected" and random.random() < 0.6
        gt_prob = round(random.uniform(0.2, 0.9), 2) if gt_recoverable else 0.0
        txs.append({
            "transaction_id": f"txn_{i}",
            "customer_id": cid,
            "amount": random.randint(1000, 10000),
            "status": "failed",
            "error_code": code,
            "_ground_truth_recoverable": gt_recoverable,
            "_ground_truth_recovery_probability": gt_prob,
        })
    return txs


def test_phase3_end_to_end_runs():
    customers = _make_customers(20)
    txs = _make_transactions(customers, n=60)

    # baseline
    baseline_metrics = run_retry_all_3(txs, seed=42)
    assert "RAR" in baseline_metrics and "RR" in baseline_metrics

    # ReviveAI simulation
    orchestrator = Orchestrator()
    llm = LLMService()
    rz = FakeRazorpayClient()
    revive_metrics = run_reviveai(orchestrator, txs, customers, seed=42)
    assert "RAR" in revive_metrics and "RR" in revive_metrics
    # Ensure outputs are numbers
    assert isinstance(revive_metrics["recovery_rate"], float)

