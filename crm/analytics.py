import math
from collections import Counter
from dataclasses import dataclass

from django.db.models import Avg, Count, Sum

from concierge.engine import classify_topics

from .models import Conversation, Lead, Message

CHART_COLORS = ["#5E1224", "#A8834A", "#6F7D66", "#B9776A", "#7A6E64", "#D8C39A", "#2A211C"]
DONUT_RADIUS = 70
DONUT_CIRCUMFERENCE = 2 * math.pi * DONUT_RADIUS


@dataclass
class Segment:
    name: str
    value: int
    percent: int
    color: str
    dash: float
    offset: float


def department_mix() -> tuple[list[Segment], int]:
    rows = list(Conversation.objects.values("department").annotate(n=Count("id")).order_by("-n", "department"))
    total = sum(r["n"] for r in rows) or 1
    gap = 3 if len(rows) > 1 else 0
    segments, offset = [], 0.0
    for i, row in enumerate(rows):
        length = row["n"] / total * DONUT_CIRCUMFERENCE
        segments.append(
            Segment(
                row["department"],
                row["n"],
                round(row["n"] / total * 100),
                CHART_COLORS[i % len(CHART_COLORS)],
                round(max(length - gap, 0.5), 2),
                round(-offset, 2),
            )
        )
        offset += length
    return segments, sum(r["n"] for r in rows)


def lead_funnel() -> list[dict]:
    stages = list(Lead.Stage)
    counts = Counter(Lead.objects.values_list("stage", flat=True))
    rows, previous = [], None
    for i, stage in enumerate(stages):
        value = sum(counts[s] for s in stages[i:])
        rows.append(
            {
                "name": stage.label,
                "value": value,
                "conversion": round(value / previous * 100) if previous else None,
                "opacity": round(1 - i * 0.12, 2),
            }
        )
        previous = value
    peak = max((r["value"] for r in rows), default=0) or 1
    for row in rows:
        row["width"] = max(round(row["value"] / peak * 100), 4)
    return rows


def popular_destinations() -> list[dict]:
    rows = list(Lead.objects.values("destination").annotate(n=Count("id")).order_by("-n", "destination"))
    peak = max((r["n"] for r in rows), default=1)
    return [{"name": r["destination"], "value": r["n"], "width": round(r["n"] / peak * 100)} for r in rows]


def visitor_topics(limit: int = 5) -> list[dict]:
    counter: Counter[str] = Counter()
    for text in Message.objects.filter(role=Message.Role.VISITOR).values_list("text", flat=True):
        counter.update(classify_topics(text))
    total = sum(counter.values()) or 1
    return [{"name": name, "percent": round(n / total * 100)} for name, n in counter.most_common(limit)]


def pipeline_stats() -> dict:
    agg = Lead.objects.aggregate(count=Count("id"), guests=Sum("guests"), score=Avg("score"))
    return {
        "leads": agg["count"],
        "guests": agg["guests"] or 0,
        "avg_score": round(agg["score"] or 0),
        "departments": Conversation.objects.values("department").distinct().count(),
    }
