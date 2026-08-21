from __future__ import annotations
from typing import Literal


State = Literal[
    "NEW",
    "DETECTED",
    "DIAGNOSING",
    "DIAGNOSED",
    "SCORING",
    "SCORED",
    "DECIDING",
    "DECIDED",
    "POLICY_CHECK",
    "APPROVED",
    "EXECUTING",
    "EXECUTED",
    "EVALUATING",
    "RECOVERED",
    "RETRY_SCHEDULED",
    "ESCALATED",
    "ABANDONED",
]


class StateMachine:
    def __init__(self, initial: State = "NEW") -> None:
        self.state: State = initial

    def transition(self, new_state: State) -> None:
        # minimal validation: allow any forward progression
        self.state = new_state

    def step(self, event: str) -> None:
        # simple event-driven stepper for common events
        if self.state == "NEW" and event == "detect":
            self.transition("DETECTED")
        elif self.state == "DETECTED" and event == "diagnose":
            self.transition("DIAGNOSING")
        elif self.state == "DIAGNOSING" and event == "done":
            self.transition("DIAGNOSED")
        elif self.state == "DIAGNOSED" and event == "score":
            self.transition("SCORING")
        elif self.state == "SCORING" and event == "done":
            self.transition("SCORED")
        elif self.state in {"SCORED", "DIAGNOSED"} and event == "decide":
            self.transition("DECIDING")
        elif self.state == "DECIDING" and event == "done":
            self.transition("DECIDED")
        elif self.state == "DECIDED" and event == "policy":
            self.transition("POLICY_CHECK")
        elif self.state == "POLICY_CHECK" and event == "approved":
            self.transition("APPROVED")
        elif self.state == "APPROVED" and event == "execute":
            self.transition("EXECUTING")
        elif self.state == "EXECUTING" and event == "done":
            self.transition("EXECUTED")
        elif self.state == "EXECUTED" and event == "evaluate":
            self.transition("EVALUATING")
        elif self.state == "EVALUATING" and event == "recovered":
            self.transition("RECOVERED")
        elif self.state == "EVALUATING" and event == "retry":
            self.transition("RETRY_SCHEDULED")
        elif event == "escalate":
            self.transition("ESCALATED")
        elif event == "abandon":
            self.transition("ABANDONED")
