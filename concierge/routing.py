"""Choosing the team a conversation is handed to.

Evaluated on realistic handoff conversations (see tests/test_routing.py):
Gemini with explicit team definitions handled phrasing the rules never saw
("our mehendi is Saturday and the band isn't confirmed", "we own a haveli,
would you list us?"), while the weighted rules are never confidently wrong.

Policy, in order:
1. Gemini names a specific team with confidence >= AI_CONFIDENCE (AI_CONFIDENCE_NO_EVIDENCE when the
   conversation contains no routing keywords at all: an AI call with nothing to go on must be very sure) → use it.
2. The rules are confident (enough weighted evidence, clear leader) → use them.
3. Otherwise ask the visitor, with one-tap team choices.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ai import classify_department
from .engine import ConciergeState, Department, route_by_rules

AI_CONFIDENCE = 0.8
AI_CONFIDENCE_NO_EVIDENCE = 0.9


@dataclass(frozen=True)
class RoutingDecision:
    department: Department | None  # None: ask the visitor
    source: str  # "ai", "rules", "visitor" or "ask"
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
        # The latest message named no team, but the conversation was already about one.
        return RoutingDecision(state.department, "rules", rules.confidence, f"Continuing the conversation's topic ({state.department})")

    return RoutingDecision(None, "ask", 0.0, "Not enough information to choose a team")


def visitor_choice(department: Department, answer: str) -> RoutingDecision:
    return RoutingDecision(department, "visitor", 1.0, f"Visitor chose “{answer[:80]}”")


def accepted_offer(department: Department) -> RoutingDecision:
    return RoutingDecision(department, "visitor", 1.0, f"Visitor accepted the concierge’s offer to connect them with {department}")
