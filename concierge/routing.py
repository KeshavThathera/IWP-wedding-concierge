from __future__ import annotations

from dataclasses import dataclass

from .ai import classify_department
from .engine import ConciergeState, Department, route_by_rules

AI_CONFIDENCE = 0.8
AI_CONFIDENCE_NO_EVIDENCE = 0.9


@dataclass(frozen=True)
class RoutingDecision:
    department: Department | None  # None = ask the visitor
    source: str
    confidence: float
    reason: str


def decide_team(state: ConciergeState, budget_scope: str = "routing") -> RoutingDecision:
    rules = route_by_rules(state.visitor_texts)
    ai = classify_department(state, budget_scope)

    threshold = AI_CONFIDENCE if rules.evidence else AI_CONFIDENCE_NO_EVIDENCE
    if ai and ai.department != Department.GENERAL and ai.confidence >= threshold:
        reason = ai.reason
        if rules.department and rules.department != ai.department:
            reason += f" (keyword rules suggested {rules.department})"
        return RoutingDecision(ai.department, "ai", ai.confidence, reason)

    if rules.department:
        return RoutingDecision(
            rules.department,
            "rules",
            rules.confidence,
            f"Clear keyword evidence across the conversation ({rules.confidence:.0%} of signals)",
        )

    if state.department != Department.GENERAL:
        # nothing new in the last message, keep the conversation's topic
        return RoutingDecision(state.department, "rules", rules.confidence, f"Continuing the conversation's topic ({state.department})")

    return RoutingDecision(None, "ask", 0.0, "Not enough information to choose a team")


def visitor_choice(department: Department, answer: str) -> RoutingDecision:
    return RoutingDecision(department, "visitor", 1.0, f"Visitor chose '{answer[:80]}'")


def accepted_offer(department: Department) -> RoutingDecision:
    return RoutingDecision(department, "visitor", 1.0, f"Visitor accepted the concierge's offer to connect them with {department}")
