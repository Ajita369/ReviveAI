from __future__ import annotations
from typing import Dict, Any
from services.policy_engine import PolicyEngine
from services.scoring_engine import ScoringEngine
from agent.state_machine import StateMachine


class Orchestrator:
    def __init__(self) -> None:
        self.policy = PolicyEngine()
        self.scoring = ScoringEngine()
        self.machine = StateMachine()

    def decide_action(self, tx: Dict[str, Any], customer: Dict[str, Any]) -> str:
        score = self.scoring.score(tx, customer)
        ros = score["ros"]
        if ros >= 0.7:
            return "retry"
        if ros >= 0.4:
            return "payment_link"
        if ros >= 0.2:
            return "reminder"
        return "no_action"

    def process(self, tx: Dict[str, Any], customer: Dict[str, Any]) -> Dict[str, Any]:
        # drive state machine and make a policy-checked decision
        self.machine.step("detect")
        self.machine.step("diagnose")
        self.machine.step("done")  # diagnosed
        self.machine.step("score")
        score = self.scoring.score(tx, customer)
        self.machine.step("done")  # scored
        self.machine.step("decide")
        action = self.decide_action(tx, customer)
        self.machine.step("done")  # decided
        self.machine.step("policy")
        validation = self.policy.validate(action, tx)
        if validation.get("approved"):
            self.machine.step("approved")
            # here, executing would call payment provider; we simulate
            self.machine.step("execute")
            self.machine.step("done")
            self.machine.step("evaluate")
            result = {"status": "executed", "action": action}
            # simulate simple evaluation
            if tx.get("_ground_truth_recoverable") and tx.get("_ground_truth_recovery_probability", 0) > 0.0:
                result["outcome"] = "success_simulated"
            else:
                result["outcome"] = "failed_simulated"
        else:
            # not approved by policy
            self.machine.step("abandon")
            result = {"status": "policy_blocked", "action": action, "checks": validation.get("checks")}

        return {"transaction_id": tx.get("transaction_id"), "score": score, "validation": validation, "result": result, "state": self.machine.state}
