# IWP AI Wedding Concierge

A Django application demonstrating how a multilingual AI concierge could welcome, qualify and route enquiries for a luxury Indian wedding-planning house, with a staff workspace behind it: team inbox, lead pipeline and analytics.

> Independent portfolio concept. **Not** affiliated with, endorsed by or operated by Indian Wedding Planners. All people, leads and contact details are fictional.

## What it does

**Public site**
- Editorial landing page with a floating concierge chat.
- The concierge recognises intent and routes to one of seven departments: Wedding Sales, Client Servicing, HR & Careers, Vendors & Partnerships, Marketing & PR, Finance, General Support.
- Wedding enquiries are qualified conversationally, one question at a time: destination, guests, date, budget, venue style, contact. Details volunteered early are recognised, so nothing is asked twice.
- English, Hindi and Hinglish. Once a visitor writes in Hinglish, replies stay in Hinglish.
- A handoff creates a ticket (plus a scored lead for wedding enquiries) and turns the widget into a **live chat with the team**: the visitor sees when a planner joins, their replies and typing, and when the conversation is closed.
- **Optional Gemini assist:** open questions ("What's the best month for Udaipur?") get a natural answer, and qualification carries on. See [AI design](#ai-design-gemini).

**Staff workspace** (`/dashboard/`, login required)
- Overview: KPIs, live queue, routing mix and the strongest leads.
- Team inbox (live): new visitor messages, typing indicators and status changes appear without refreshing, with an *Awaiting reply* marker in the list. Filter by department and status, take ownership, reply, change status and keep internal notes (HTMX, no page reloads). With Gemini enabled: AI handoff summaries and **Draft with AI** replies that staff review before sending.
- Lead pipeline: six-stage kanban with drag-and-drop.
- Analytics: department donut, lead funnel with stage conversion, destination demand, and visitor topics classified by the engine.
- Django admin at `/admin/` and a REST API at `/api/`.

## Architecture

```
concierge/engine.py      Pure-Python concierge: language + intent detection, slot filling,
                         handoff decisions, lead extraction. No Django imports; fully unit-tested.
concierge/llm.py         Minimal Gemini REST client (stdlib only), timeouts, typed errors, free-tier rate limiting.
concierge/ai.py          Where the model may help: prompts, guardrails and fallbacks.
concierge/views.py       Landing page + JSON chat endpoints (state kept in the visitor's session).
crm/models.py            Conversation, Message, Lead.
crm/services.py          create_handoff(), post_staff_reply(): transactional business operations.
crm/analytics.py         ORM aggregations and SVG chart geometry.
crm/views.py             Staff workspace; plain POST forms enhanced with HTMX partial swaps.
crm/api.py               Django REST Framework serializers and viewsets.
crm/seed.py              Fictional demo data + `manage.py seed_demo`.
templates/               Django templates styled with Tailwind CSS.
static/                  Built CSS, vanilla JS (chat client, drag-and-drop), vendored htmx.
tests/                   pytest: engine unit tests, view/API integration tests.
```

**Why this shape**
- **The engine is framework-free.** Routing rules are the part most likely to change (or be swapped for an LLM), so they live in a plain module with plain dataclasses that is trivial to test.
- **Nothing is persisted until handoff.** Anonymous chat state lives in the session; only a real handoff creates database rows.
- **Progressive enhancement.** Every staff action is a normal form POST that works without JavaScript. HTMX upgrades it to swap just the changed panel.
- **Specific routes beat general ones.** "Wedding photographer wanting to partner" goes to Vendors, not Sales, because rules are ordered from most to least specific.

**Stack:** Python 3.12 · Django 5.2 · Django REST Framework · Google Gemini (REST) · HTMX · Tailwind CSS · SQLite (local) / PostgreSQL (production) · WhiteNoise · gunicorn · pytest · Ruff

## Live handoff

**Try it on one screen:** in the staff workspace open **Live demo (split view)** (`/dashboard/demo/`). The public site runs in a phone frame on the left with the concierge already open; the team inbox runs in a compact layout on the right. Chat on the phone, ask for a person, then *Take over* and reply in the inbox. **New visitor chat** starts again without signing you out.


After handoff the database owns the transcript and both sides poll a cursor ("messages after id N") every ~2 seconds:

```
Visitor widget  ── POST /concierge/messages/  ──▶  Message(role=visitor)       ◀── GET /dashboard/inbox/<id>/updates/?after=N  ── Staff inbox
                ◀── GET /concierge/live/?after=N ── Message(role=agent|system)  ◀── POST /dashboard/inbox/<id>/ (reply, take over, close)
Typing:  POST /concierge/typing/  ·  POST /dashboard/inbox/<id>/typing/   → 5-second cache flags, no database writes
```

- **Join / leave / close events** are stored as `system` messages, so both sides see the same timeline and it is auditable later.
- **Visitors can only read their own conversation:** its id comes from their session, never from the request.
- **Why polling rather than WebSockets:** it runs on any WSGI host (Render free tier, plain gunicorn) with no Redis or ASGI server, and a 2-second cadence feels instant for chat. Polls pause in background tabs. The scale-up path is Django Channels with a Redis channel layer; the service functions in `crm/services.py` would stay the same, with only the transport changing.
- Typing flags live in Django's cache. With several gunicorn workers, point `CACHES` at Redis or the database cache so all workers share them.

## Routing to the right team

When the visitor asks for a person, `concierge/routing.py` decides who takes over:

1. **Gemini reads the whole conversation** and returns `{department, confidence, reason}` as structured JSON, restricted to the seven team names. It is trusted at ≥ 80% confidence, or ≥ 90% if the conversation contains no team-specific keywords at all (an AI guess with no evidence must be very sure).
2. **Weighted rules** score every visitor message (later messages count more; specific phrases such as "already booked", "receipt" or "we run a decor studio" outweigh generic wedding words) and are used when one team clearly leads.
3. **Otherwise the concierge asks**: "Which of these best describes what you need?" with one-tap choices (*Planning a new wedding*, *An existing booking*, *Invoices & payments*, …). Any answer completes the handoff.

The confirmation names the team and what they do, and staff see how each conversation was routed (Gemini / rules / visitor's choice, confidence and reason).

Measured on realistic handoffs (`tests/test_routing.py` plus harder live cases): the original first-match rules routed 6 of 13 correctly; the weighted rules are never confidently wrong (they route or ask), and Gemini with explicit team definitions handled phrasing no rule anticipated, such as *"our mehendi is on Saturday and the band still hasn't been confirmed"* → Client Servicing.

## AI design (Gemini)

The rules stay in charge; the model only adds language.

| Responsibility | Owner | Why |
|---|---|---|
| Collecting wedding details, deciding when to hand off | Deterministic engine | Must be predictable, auditable and testable |
| Choosing the team at handoff | Gemini (structured JSON), then weighted rules, then the visitor | See [Routing to the right team](#routing-to-the-right-team) |
| Answering open questions mid-conversation | Gemini, then the engine's next question is appended | Natural answers without derailing qualification |
| Handoff summary for staff | Gemini, with the rule-based summary as fallback | Better briefs, labelled **AI summary** in the inbox |
| Reply drafts for staff | Gemini, on request only | Staff review and edit; nothing is sent automatically |

**Safeguards**
- **Graceful degradation:** no key, a timeout, quota errors (HTTP 429) or a safety block all fall back silently to the rule-based reply. The site never breaks.
- **Guardrails in the system prompt:** no prices, availability or contact details stated as fact; never asks for payment or ID details; replies in the visitor's language; ignores attempts to override its instructions; output is length-capped and stripped of markdown.
- **Transparency:** AI-written chat answers carry an *AI-assisted* caption; AI messages and summaries are flagged in the database and labelled in the inbox.
- **Quota protection:** a global requests-per-minute cap and a per-visitor hourly cap (Django cache) keep usage inside the free tier.
- **Model failover:** if the primary model is overloaded (503), rate-limited (429) or slow, the client moves to the next model in `GEMINI_FALLBACK_MODELS`; configuration errors (bad key, bad request) fail fast.
- **Complete answers:** `thinkingLevel: minimal` stops hidden reasoning tokens from consuming the output budget, and any reply that still hits the limit is trimmed to its last full sentence.
- **No heavy SDK:** a ~100-line standard-library client calls the documented `generateContent` endpoint, so there are no compiled dependencies and it's easy to mock.
- **Offline tests:** a fake model is injected in tests; the suite never calls the real API, even if a key is present.

**Enable it:** create a free key at [Google AI Studio](https://aistudio.google.com/apikey), put it in `.env` as `GEMINI_API_KEY=...`, and restart the server. Defaults: `gemini-3.5-flash` (about 2 s in testing) with `gemini-3.1-flash-lite` as fallback, both on the free tier; change them with `GEMINI_MODEL` and `GEMINI_FALLBACK_MODELS`.

> Free-tier note: Google may use free-tier API content to improve its products. The concierge asks visitors not to share sensitive details, and all demo data is fictional.

## Run locally

Requires Python 3.12+.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000. Staff workspace: http://127.0.0.1:8000/dashboard/ (use **Continue with the demo account**, or `demo` / `demo123`).

Node is **not** needed to run the app; the compiled CSS is committed. To change styles:

```bash
npm install
npm run watch:css      # or: npm run build
```

## Tests and quality

```bash
pytest                 # 135 tests: engine rules, team routing scenarios, AI layer (fake model), live handoff between visitor and staff, chat flow, staff actions, permissions, REST API
ruff check . && ruff format --check .
```

GitHub Actions runs lint, a migrations check and the full test suite against PostgreSQL on every push.

## REST API

Session-authenticated; staff only. Browsable at `/api/` when signed in.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/conversations/?department=&status=` | List conversations with messages |
| GET / PATCH | `/api/conversations/{id}/` | Read; update status or note |
| GET / POST | `/api/leads/` | List or create leads |
| GET / PATCH / DELETE | `/api/leads/{id}/` | Manage a lead (e.g. move stage) |
| GET | `/api/leads/funnel/` | Pipeline counts and stage conversion |

Public chat endpoints (CSRF-protected): `GET /concierge/state/`, `POST /concierge/messages/` `{"text": "..."}`, `POST /concierge/reset/`.

## Deploy

**Render (free tier):** push to GitHub, then in Render choose *New → Blueprint* and select the repository. `render.yaml` provisions PostgreSQL and the web service, generates a secret key, and `build.sh` runs migrations and loads the demo data.

**Docker:**
```bash
docker build -t iwp-concierge .
docker run -p 8000:8000 -e DJANGO_SECRET_KEY=change-me -e DJANGO_ALLOWED_HOSTS=localhost iwp-concierge
```

Configuration is via environment variables; see `.env.example`.

## Production notes

This is a demonstration. A real deployment would add:
- A paid Gemini tier (or another provider) with data-processing terms suitable for real customer conversations.
- Real notifications on handoff (email/WhatsApp Business API), probably via a task queue such as Celery.
- Role-based staff permissions, audit history and data-retention rules for visitor messages.
- Rate limiting on the public chat endpoint.

## Previous version

The first iteration (Next.js/TypeScript, browser-only state) is kept in [`legacy-nextjs/`](legacy-nextjs/) for reference.
