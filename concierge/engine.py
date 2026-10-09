"""Deterministic concierge engine.

Pure Python with no Django imports, so the routing and qualification rules can
be unit-tested in isolation. The web layer stores a ``ConciergeState`` in the
visitor's session and calls :func:`take_turn` for each message.

Flow:
1. Detect the visitor's language (English vs Hindi/Hinglish) and department.
2. Wedding Sales enquiries are qualified one detail at a time (destination,
   guests, date, budget, style, contact); details volunteered early are
   recognised so the visitor is never asked twice.
3. Other departments collect a contact detail, then offer a human handoff.
4. Asking for a person, or accepting an offered handoff, ends the turn with a
   handoff, which the web layer turns into a ticket in the staff inbox.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Literal

Lang = Literal["en", "hi"]


class Department(StrEnum):
    WEDDING_SALES = "Wedding Sales"
    CLIENT_SERVICING = "Client Servicing"
    HR_CAREERS = "HR and Careers"
    VENDORS = "Vendors and Partnerships"
    MARKETING = "Marketing and PR"
    FINANCE = "Finance"
    GENERAL = "General Support"


class Slot(StrEnum):
    DESTINATION = "destination"
    GUESTS = "guests"
    DATE = "date"
    BUDGET = "budget"
    STYLE = "style"
    CONTACT = "contact"


SLOT_ORDER: tuple[Slot, ...] = tuple(Slot)
QUESTION_FACT_SLOTS = frozenset({Slot.DESTINATION, Slot.GUESTS})

OPENING = (
    "Namaste, and welcome. I’m the IWP wedding concierge. I can help you explore destinations, "
    "begin planning your celebration or reach the right member of our team. How may I help?"
)
QUICK_ACTIONS = (
    "Plan my wedding",
    "Explore venues",
    "Understand budgets",
    "Careers",
    "Vendor collaboration",
    "Existing client support",
    "Speak to a person",
)

DESTINATIONS = ("jaipur", "udaipur", "goa", "jodhpur", "kerala", "mussoorie", "jim corbett", "thailand", "bali", "dubai")

SLOT_PATTERNS: dict[Slot, re.Pattern[str]] = {
    Slot.DESTINATION: re.compile("|".join(DESTINATIONS) + "|abroad", re.I),
    Slot.GUESTS: re.compile(r"\d{2,4}\s*(?:guests?|people|log|pax|mehmaan)", re.I),
    Slot.DATE: re.compile(
        r"january|february|march|april|may|june|july|august|september|october|november|december|winter|summer|monsoon|\b20\d\d\b", re.I
    ),
    Slot.BUDGET: re.compile(r"₹|\brs\.?|\binr\b|lakh|crore|\bcr\b|no limit", re.I),
    Slot.STYLE: re.compile(r"palace|fort|beach|lake|resort|heritage|haveli", re.I),
    Slot.CONTACT: re.compile(r"@|\+?\d[\d\s-]{8,}|whatsapp|phone|email|call", re.I),
}

QUESTIONS: dict[Lang, dict[Slot, str]] = {
    "en": {
        Slot.DESTINATION: "How lovely. Is there a destination—or a kind of setting—you find yourselves drawn to?",
        Slot.GUESTS: "Approximately how many guests are you hoping to welcome?",
        Slot.DATE: "Which month or season are you considering for the celebration?",
        Slot.BUDGET: "Do you have a comfortable budget range in mind? An approximate figure is perfectly fine.",
        Slot.STYLE: "Which setting feels most like you: a palace, a fort, a lakeside terrace, a beach or a resort?",
        Slot.CONTACT: "Finally, how would you prefer our planners reach you—phone, WhatsApp or email?",
    },
    "hi": {
        Slot.DESTINATION: "Bahut sundar! Aap kis destination ya kis tarah ki setting ke baare mein soch rahe hain?",
        Slot.GUESTS: "Lagbhag kitne mehmaan aane ki ummeed hai?",
        Slot.DATE: "Shaadi ke liye kaun sa mahina ya season soch rahe hain?",
        Slot.BUDGET: "Kya aapke mann mein koi budget range hai? Andaaza bhi kaafi hai.",
        Slot.STYLE: "Aapko kaun si setting sabse zyada pasand hai: palace, fort, lakeside, beach ya resort?",
        Slot.CONTACT: "Aakhir mein, hamare planners aapse kaise sampark karein—phone, WhatsApp ya email?",
    },
}

DESTINATION_INTROS = {
    "jaipur": "Jaipur is extraordinary for heritage-palace celebrations—courtyards, mirrored halls and a truly royal scale.",
    "udaipur": "Udaipur is made for lakeside grandeur—sunset terraces, palace views across the water and an intimate elegance.",
    "jodhpur": "Jodhpur brings drama: fort ramparts, desert evenings and the blue city glowing below.",
    "goa": "Goa suits relaxed, barefoot celebrations—sunlit beaches and multi-day festivities by the sea.",
    "kerala": "Kerala offers serene backwater and coastal settings, lush and wonderfully calm.",
}

DEPARTMENT_OPENERS = {
    Department.HR_CAREERS: "Thank you for your interest in joining us. I’ve noted this for our HR and Careers team. What email address should they use to reach you?",
    Department.VENDORS: "How lovely—we always enjoy meeting new creative partners. Could you share your name or studio name, along with a contact email?",
    Department.CLIENT_SERVICING: "I understand this may be time-sensitive, and I’ve marked it as a priority for Client Servicing. Shall I connect you with a team member now?",
    Department.FINANCE: "Of course. I’ve routed this to our Finance team. Please share your name and the email linked to your booking—no card or bank details, please.",
    Department.MARKETING: "Thank you for reaching out. I’ve noted this for Marketing and PR. Could you share your publication or brand, and a contact email?",
}

# Routing signals: (pattern, weight). Strong, specific phrases outweigh generic wedding words,
# so "our wedding is next week and the decorator hasn't confirmed" is an existing client,
# and "wedding photographer keen to partner" is a vendor.
DEPARTMENT_SIGNALS: dict[Department, tuple[tuple[re.Pattern[str], float], ...]] = {
    Department.CLIENT_SERVICING: (
        (
            re.compile(
                r"already (a )?client|existing (client|booking)|booked (with|through) you|we('ve| have)? booked|i('ve| have)? booked", re.I
            ),
            3,
        ),
        (re.compile(r"\b(my|our) (booking|planner|coordinator|event manager)\b|meri booking|hamari booking|booking hai|मेरी बुकिंग", re.I), 3),
        (re.compile(r"\b(our|my) (wedding|event|function|sangeet|reception) is (next|this|tomorrow|today|in \d+)", re.I), 3),
        (re.compile(r"\b(change|update|reschedule|cancel)\b.{0,30}\b(date|guest|venue|booking|count|list|menu)", re.I), 2),
        (re.compile(r"urgent|asap|emergency|airport transfer|hasn'?t (arrived|confirmed|shown)|not (arrived|confirmed)", re.I), 1.5),
    ),
    Department.FINANCE: (
        (
            re.compile(
                r"invoice|receipt|refund|\bgst\b|payment|\bpaid\b|advance (amount|payment)?|balance (amount|due)|\bbill(ing)?\b", re.I
            ),
            3,
        ),
        (re.compile(r"\baccounts?\b|finance|transaction|bank transfer", re.I), 2),
    ),
    Department.HR_CAREERS: (
        (
            re.compile(
                r"\bjobs?\b|career|hiring|vacanc|internships?|\bintern\b|resume|\bcv\b|recruit|apply for|job opening|naukri|नौकरी", re.I
            ),
            3,
        ),
        (re.compile(r"join your team|work (for|with|at) (you|iwp)|\bhr\b|human resources", re.I), 2),
        (
            re.compile(
                r"\b(an|any) (opening|vacancy|position|role)s?\b|years of experience|experience in (event|wedding|hospitality)", re.I
            ),
            3,
        ),
    ),
    Department.VENDORS: (
        (re.compile(r"vendor|supplier|empanel|collaborat|partnership|partner with (you|iwp)|become a partner", re.I), 3),
        (
            re.compile(
                r"(i am|i'm|we are|we're|we run) (a|an)? ?.{0,30}(photograph|decor|florist|cater|studio|makeup|mehndi artist|\bdj\b|band|choreograph|tent|light)",
                re.I,
            ),
            3,
        ),
        (re.compile(r"\bour (studio|company|agency|firm|portfolio)\b|work on your (weddings|events)|your vendor list", re.I), 2),
        (
            re.compile(
                r"\b(we|i) (own|run|manage) (a|an|the)? ?.{0,25}(venue|haveli|hotel|resort|palace|property|farmhouse)|list us\b|venue partner",
                re.I,
            ),
            3,
        ),
        # Offering services, not seeking them: "I need a photographer" is a couple, so bare job titles don't count.
        (
            re.compile(
                r"(photographer|videographer|decorator|florist|caterer|makeup artist)s? here\b|keen to (partner|collaborate)"
                r"|(want|would love|looking|keen) to (partner|work|collaborate) with|partner (up )?with",
                re.I,
            ),
            3,
        ),
    ),
    Department.MARKETING: (
        (
            re.compile(
                r"\bpress\b|\bmedia\b|magazine|journalist|editor|influencer|content creator|instagram|youtube|blog|interview|\bpr\b|marketing",
                re.I,
            ),
            3,
        ),
        (re.compile(r"feature (you|your|iwp)|write (about|for)|cover (your|a) (wedding|story)", re.I), 2),
        (re.compile(r"\bcollab\b|followers|\bcreator\b|brand (deal|partnership)|sponsor", re.I), 3),
    ),
    Department.WEDDING_SALES: (
        (
            re.compile(
                r"getting married|plan(ning)? (my|our|a|the)? ?(wedding|shaadi|event)|wedding planner|destination wedding|plan my", re.I
            ),
            2,
        ),
        (re.compile(r"wedding|venue|" + "|".join(DESTINATIONS) + r"|guests?|budget|engagement|sangeet|reception|शादी|shaadi", re.I), 1),
    ),
}
# Tie-break order: more specific needs first.
DEPARTMENT_PRIORITY = (
    Department.CLIENT_SERVICING,
    Department.FINANCE,
    Department.HR_CAREERS,
    Department.VENDORS,
    Department.MARKETING,
    Department.WEDDING_SALES,
)
ROUTING_CONFIDENCE = 0.6  # share of the routing evidence the leading team needs before we trust it

TEAM_CHOICES: dict[str, Department] = {
    "Planning a new wedding": Department.WEDDING_SALES,
    "An existing booking": Department.CLIENT_SERVICING,
    "Invoices & payments": Department.FINANCE,
    "Careers at IWP": Department.HR_CAREERS,
    "Vendor partnership": Department.VENDORS,
    "Press & marketing": Department.MARKETING,
    "Something else": Department.GENERAL,
}
TEAM_QUESTION: dict[Lang, str] = {
    "en": "Of course, I’ll connect you with the right person. Which of these best describes what you need?",
    "hi": "Zaroor, main aapko sahi team se jodta hoon. Aapko kis cheez mein madad chahiye?",
}
TEAM_BLURBS: dict[Department, str] = {
    Department.WEDDING_SALES: "who plan new celebrations",
    Department.CLIENT_SERVICING: "who look after confirmed bookings",
    Department.FINANCE: "who handle invoices, payments and refunds",
    Department.HR_CAREERS: "who look after careers and internships",
    Department.VENDORS: "who work with our creative partners",
    Department.MARKETING: "who handle press and collaborations",
    Department.GENERAL: "who will make sure you reach the right person",
}

FALLBACKS: dict[Lang, str] = {
    "en": "I can help with wedding planning, destinations, careers, vendor partnerships, client support or finance. Which would you like to explore?",
    "hi": "बिल्कुल। मैं हिंदी या Hinglish में आपकी मदद कर सकता हूँ। क्या आप शादी की planning कर रहे हैं, venue देखना चाहते हैं, या team से बात करना चाहते हैं?",
}

HUMAN_REQUEST = re.compile(
    r"\b(human|real person|actual person|a person|representative|team member|customer care)\b"
    r"|\b(speak|talk|chat)\s+(to|with)\b|\bcall (me|back)\b|\bcallback\b|\bconnect me\b|\bget in touch\b|\bcontact me\b"
    r"|\b(someone|somebody)\b.{0,30}\b(call|help|speak|talk|contact|reach)\b|\b(call|speak|talk|contact|reach)\b.{0,20}\b(someone|somebody)\b"
    r"|\b(a|my|the|your) (planner|team)\b.{0,20}\b(call|contact|reach)\b"
    r"|\b(get|find|send|need|want)( me)? (someone|somebody|a person|a human|a planner)\b"
    r"|\bwho (can|could|should|will) (help|assist)\b|\bwho (can|do|should) i (contact|reach|ask|write to|call)\b"
    r"|इंसान|baat kar|call kar|kisi se",
    re.I,
)
AFFIRMATIVE = re.compile(r"^(yes|yeah|yep|sure|ok|okay|please|haan|ha|ji|haanji|zaroor|bilkul|go ahead|do it)\b", re.I)
NEGATIVE = re.compile(r"^(no|nope|not now|nahi|nahin|later)\b", re.I)
QUESTION = re.compile(
    r"\?\s*$|^(what|how|when|where|which|why|who|can|could|is|are|do|does|should|will|would|tell me|suggest|recommend"
    r"|kya|kab|kaun|kaise|kitna|kitne|kahan)\b",
    re.I,
)
HINGLISH = re.compile(r"[ऀ-ॿ]|\b(main|mein|hai|hoon|kar raha|kar rahi|shaadi|chahiye|kya|aap|nahi|haan|hum)\b", re.I)

TOPIC_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Destination & venue", re.compile("venue|palace|fort|beach|lake|resort|" + "|".join(DESTINATIONS), re.I)),
    ("Budget guidance", re.compile(r"budget|₹|lakh|crore|\bcr\b|cost|price", re.I)),
    ("Dates & availability", re.compile(SLOT_PATTERNS[Slot.DATE].pattern + r"|date|available", re.I)),
    ("Careers", DEPARTMENT_SIGNALS[Department.HR_CAREERS][0][0]),
    ("Vendor partnerships", DEPARTMENT_SIGNALS[Department.VENDORS][0][0]),
    ("Client support", DEPARTMENT_SIGNALS[Department.CLIENT_SERVICING][0][0]),
    ("Invoices & payments", DEPARTMENT_SIGNALS[Department.FINANCE][0][0]),
)


def is_question(text: str) -> bool:
    """True for open questions the visitor wants answered, as opposed to answers to ours."""
    return bool(QUESTION.search(text.strip()))


def detect_lang(text: str) -> Lang:
    return "hi" if HINGLISH.search(text) else "en"


MIN_EVIDENCE = 0.5  # roughly one generic mention in the previous message
RECENCY_DECAY = 0.6  # each earlier message counts 60% as much as the one after it: needs change mid-chat
WEAK_SIGNAL = 1  # generic words ("wedding", "guests") that only count when nothing more specific is said


def score_departments(texts: list[str]) -> dict[Department, float]:
    """Weighted evidence per team, dominated by the latest messages."""
    scores = dict.fromkeys(DEPARTMENT_PRIORITY, 0.0)
    for i, text in enumerate(texts):
        recency = RECENCY_DECAY ** (len(texts) - 1 - i)
        found = {d: max((w for pattern, w in signals if pattern.search(text)), default=0) for d, signals in DEPARTMENT_SIGNALS.items()}
        strongest = max(found.values())
        for department, weight in found.items():
            # "Change our guest count" is a client request: its "guest" shouldn't also vote for Wedding Sales.
            if weight <= WEAK_SIGNAL < strongest:
                continue
            scores[department] += recency * weight
    return scores


def detect_department(text: str, current: Department | None = None) -> Department:
    scores = score_departments([text])
    best = max(DEPARTMENT_PRIORITY, key=lambda d: (scores[d], -DEPARTMENT_PRIORITY.index(d)))
    return best if scores[best] > 0 else (current or Department.GENERAL)


@dataclass
class RuleRoute:
    department: Department | None  # None when the evidence is too weak or split to trust
    confidence: float
    scores: dict[Department, float]

    @property
    def evidence(self) -> float:
        """Total routing signal found; 0 means the conversation names no team-specific need."""
        return sum(self.scores.values())


def route_by_rules(texts: list[str]) -> RuleRoute:
    """Which team the whole conversation points to, judged by weighted rules."""
    scores = score_departments(texts)
    total = sum(scores.values())
    best = max(DEPARTMENT_PRIORITY, key=lambda d: (scores[d], -DEPARTMENT_PRIORITY.index(d)))
    confidence = scores[best] / total if total else 0.0
    trusted = scores[best] >= MIN_EVIDENCE and confidence >= ROUTING_CONFIDENCE
    return RuleRoute(best if trusted else None, round(confidence, 2), scores)


def team_from_choice(text: str) -> Department | None:
    """Map a tapped team button (or close wording) to a department."""
    cleaned = text.strip().lower()
    for label, department in TEAM_CHOICES.items():
        if cleaned == label.lower():
            return department
    detected = detect_department(text)
    return detected if detected != Department.GENERAL else None


def classify_topics(text: str) -> list[str]:
    """Topics mentioned in a piece of visitor text, used for analytics."""
    return [name for name, pattern in TOPIC_RULES if pattern.search(text)]


@dataclass
class Flow:
    asked: list[str] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)
    offered: bool = False
    contact_asked: bool = False
    choosing_team: bool = False  # We asked the visitor which team they need


@dataclass
class Turn:
    """Result of one visitor message. ``reply`` is None when a handoff is due."""

    reply: str | None
    department: Department
    flow: Flow
    lang: Lang
    team_chosen: bool = False  # The visitor picked the team themselves
    accepted_offer: bool = False  # The visitor said yes to "Shall I connect you with our X team?"

    @property
    def is_handoff(self) -> bool:
        return self.reply is None

    @property
    def is_fallback(self) -> bool:
        """The rules had nothing specific to say, so a language model may answer instead."""
        return self.reply in FALLBACKS.values()


def respond(text: str, department: Department, flow: Flow, lang: Lang) -> tuple[str | None, Flow]:
    """Decide the next reply for ``text``. Returns (None, flow) to request a handoff."""
    nxt = Flow(asked=list(flow.asked), answers=dict(flow.answers), offered=flow.offered, contact_asked=flow.contact_asked)
    stripped = text.strip()
    if HUMAN_REQUEST.search(text) or (flow.offered and AFFIRMATIVE.match(stripped)):
        return None, nxt
    if flow.offered and NEGATIVE.match(stripped):
        nxt.offered = False
        if lang == "hi":
            return "Bilkul, koi jaldi nahi. Main aur kis tarah madad kar sakta hoon?", nxt
        return "Of course—there’s no rush. Is there anything else you’d like to explore?", nxt

    if department == Department.WEDDING_SALES:
        return _qualify_wedding(text, flow, nxt, lang)

    opener = DEPARTMENT_OPENERS.get(department)
    if opener and not flow.contact_asked:
        nxt.contact_asked = True
        nxt.offered = department == Department.CLIENT_SERVICING
        return opener, nxt
    if opener:
        nxt.offered = True
        return f"Thank you, that’s noted. Shall I pass this conversation to our {department} team now?", nxt
    return FALLBACKS[lang], nxt


def _qualify_wedding(text: str, flow: Flow, nxt: Flow, lang: Lang) -> tuple[str, Flow]:
    # The latest message answers whatever was asked last (unless the visitor asked us something
    # instead); patterns catch details volunteered early.
    if flow.asked and flow.asked[-1] not in nxt.answers and not is_question(text):
        nxt.answers[flow.asked[-1]] = text
    # In a question, only destination and guest count are facts ("Can we host 300 guests in Goa?");
    # a date, budget or style mentioned in a question is hypothetical ("How much is a palace wedding?").
    asking = is_question(text)
    for slot in SLOT_ORDER:
        if asking and slot not in QUESTION_FACT_SLOTS:
            continue
        if slot.value not in nxt.answers and SLOT_PATTERNS[slot].search(text):
            nxt.answers[slot.value] = text

    if re.search(r"budget|बजट", text, re.I) and not flow.asked:
        nxt.asked.append(Slot.GUESTS.value)
        return (
            "A meaningful estimate depends on guest count, destination, venue exclusivity and the number of events. "
            "Shall we begin with how many guests you’re expecting?"
        ), nxt

    city = next((c for c in DESTINATION_INTROS if c in text.lower()), None) if Slot.DESTINATION.value not in flow.answers else None
    intro = ""
    if city:
        intro = f"{city.title()} ek behtareen choice hai! " if lang == "hi" else DESTINATION_INTROS[city] + " "

    pending = next((s for s in SLOT_ORDER if s.value not in nxt.answers), None)
    if pending:
        if not nxt.asked or nxt.asked[-1] != pending.value:
            nxt.asked.append(pending.value)
        return intro + QUESTIONS[lang][pending], nxt
    nxt.offered = True
    if lang == "hi":
        return "Shukriya! Ek planner ke liye zaroori sab kuch mil gaya hai. Kya main aapko hamari Wedding Sales team se jod doon?", nxt
    return "Thank you—that’s everything a planner needs to begin. Shall I introduce you to our Wedding Sales team?", nxt


@dataclass
class ChatMessage:
    role: Literal["visitor", "assistant"]
    text: str
    ai: bool = False  # Written (at least partly) by the language model


@dataclass
class ConciergeState:
    """Everything needed to resume a conversation; serialisable to the session."""

    messages: list[ChatMessage] = field(default_factory=lambda: [ChatMessage("assistant", OPENING)])
    department: Department = Department.GENERAL
    flow: Flow = field(default_factory=Flow)
    ticket: str | None = None
    conversation_id: int | None = None  # Set once handed off; the database then owns the transcript

    @property
    def visitor_texts(self) -> list[str]:
        return [m.text for m in self.messages if m.role == "visitor"]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["department"] = str(self.department)
        return data

    @classmethod
    def from_dict(cls, data: dict | None) -> ConciergeState:
        if not data:
            return cls()
        return cls(
            messages=[ChatMessage(**m) for m in data.get("messages", [])] or [ChatMessage("assistant", OPENING)],
            department=Department(data.get("department", Department.GENERAL)),
            flow=Flow(**data.get("flow", {})),
            ticket=data.get("ticket"),
            conversation_id=data.get("conversation_id"),
        )


def take_turn(state: ConciergeState, text: str) -> Turn:
    """Advance ``state`` with a visitor message. Mutates and returns the turn result."""
    text = text.strip()
    # Once a visitor writes in Hindi or Hinglish, keep replying that way.
    lang = detect_lang(" ".join([*state.visitor_texts, text]))
    if state.flow.choosing_team:
        # Whatever they answer, connect them now: their pick, a clear signal, or General Support to triage.
        state.messages.append(ChatMessage("visitor", text))
        state.department = team_from_choice(text) or Department.GENERAL
        state.flow = Flow()
        return Turn(reply=None, department=state.department, flow=state.flow, lang=lang, team_chosen=True)
    current = None if state.department == Department.GENERAL else state.department
    department = detect_department(text, current)
    flow = state.flow if department == state.department else Flow()
    accepting = flow.offered and bool(AFFIRMATIVE.match(text)) and department == state.department
    reply, new_flow = respond(text, department, flow, lang)

    state.messages.append(ChatMessage("visitor", text))
    state.department = department
    state.flow = new_flow
    if reply is not None:
        state.messages.append(ChatMessage("assistant", reply))
    return Turn(reply=reply, department=department, flow=new_flow, lang=lang, accepted_offer=accepting and reply is None)


def ask_for_team(state: ConciergeState, lang: Lang) -> None:
    """The visitor wants a person but we can't tell which team: ask, with one-tap choices."""
    state.messages.append(ChatMessage("assistant", TEAM_QUESTION[lang]))
    state.flow = Flow(choosing_team=True)


@dataclass
class LeadDetails:
    destination: str | None = None
    guests: int | None = None
    budget: str | None = None
    month: str | None = None
    style: str | None = None
    contact: str | None = None
    contact_method: str | None = None

    @property
    def is_qualified(self) -> bool:
        return bool(self.destination and self.guests and self.budget)

    @property
    def has_signal(self) -> bool:
        return bool(self.destination or self.guests or self.budget)

    def summary_line(self) -> str:
        parts = [self.destination, f"{self.guests} guests" if self.guests else None, self.month, self.budget, self.style]
        return " · ".join(p for p in parts if p)


BUDGET_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)\s*[\d.]+\s*(?:[-–]\s*[\d.]+)?\s*(?:cr|crore|l|lakh)?|[\d.]+\s*(?:[-–]\s*[\d.]+)?\s*(?:lakh|crore|cr)\b", re.I
)
CONTACT_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d\s-]{8,}\d")


def extract_lead(state: ConciergeState) -> LeadDetails:
    """Pull structured lead fields out of a wedding conversation."""
    answers = state.flow.answers
    everything = " ".join(state.visitor_texts)

    def first(pattern: re.Pattern[str], *sources: str) -> str | None:
        for source in sources:
            if source and (match := pattern.search(source)):
                return match.group(0).strip()
        return None

    guests = first(re.compile(r"\d{2,4}"), answers.get("guests", ""), first(SLOT_PATTERNS[Slot.GUESTS], everything) or "")
    budget = first(BUDGET_PATTERN, answers.get("budget", ""), everything) or (answers.get("budget") or "").strip() or None
    destination = first(SLOT_PATTERNS[Slot.DESTINATION], everything)
    month = first(SLOT_PATTERNS[Slot.DATE], answers.get("date", ""), everything)
    style = first(SLOT_PATTERNS[Slot.STYLE], answers.get("style", ""), everything)
    contact_text = answers.get("contact", "")
    method = first(re.compile(r"whatsapp|phone|email|call", re.I), contact_text)
    return LeadDetails(
        destination=destination.title() if destination else None,
        guests=int(guests) if guests else None,
        budget=budget,
        month=month.title() if month else None,
        style=style.title() if style else None,
        contact=first(CONTACT_PATTERN, contact_text),
        contact_method=method.title() if method else None,
    )
