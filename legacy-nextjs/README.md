> **Superseded.** This is the original Next.js/TypeScript prototype, kept for reference. The current application is the Django project in the repository root.
> To run this version: `cd legacy-nextjs && npm install && npm run dev`.

# IWP AI Wedding Concierge

An independent portfolio concept demonstrating how a multilingual AI concierge could welcome, qualify and route enquiries for a luxury Indian wedding-planning team. This is **not an official Indian Wedding Planners product or deployment**.

## The problem

Wedding enquiries arrive with very different levels of detail and intent. A planning team needs to distinguish a high-intent wedding lead from careers, vendor, finance and existing-client questions—without making the visitor fill in a long form.

## Product approach

The public landing page introduces a warm conversational experience. A deterministic concierge recognises intent, asks contextual follow-up questions one at a time and can create a simulated human handoff. The staff workspace makes seeded and newly handed-off conversations visible alongside a lead pipeline and lightweight analytics.

## Main features

- Luxury, responsive public landing page with an original AI-generated wedding visual
- Floating English, Hindi and Hinglish-friendly concierge
- Rule-based routing for Wedding Sales, Client Servicing, HR, Vendors, Marketing, Finance and General Support
- Simulated handoff with reference number, summary and complete transcript
- Team inbox with department/status filters, assignment, status and internal notes
- Movable six-stage lead pipeline
- Department, funnel, destination and topic analytics
- Browser-local persistence and seeded fictional demo data
- No paid service or API key required

## Architecture

- Next.js App Router + TypeScript
- Tailwind CSS for the design system
- Lightweight custom SVG charts (no charting dependency)
- React context plus `localStorage` for reliable, no-backend demo persistence
- Static assets in `public/`

All decisioning runs client-side for this demonstration. A production system would move routing, model calls, identity and persistence to authenticated server-side services.

## How routing works

`components/concierge-chat.tsx` uses ordered keyword rules. For wedding enquiries it tracks which details (destination, guests, date, budget, style, contact) are still missing and asks only for those, then offers a handoff. Once a visitor writes in Hindi or Hinglish, replies stay in Hinglish. High-specificity routes (careers, vendors, finance, current-client support) are evaluated before broad wedding-planning terms. The currently detected department is retained through the conversation; a request for a person preserves that route when possible. Scripted follow-up responses provide a reliable evaluation path without pretending every interaction uses live AI.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard is at `/dashboard`.

Production check:

```bash
npm run build
npm start
```

## Demo access

Use the one-click **Enter staff demo** link on the landing page. The displayed demo identity is:

- Email: `demo@iwp.local`
- Password: `demo123`

No real authentication is performed. This is intentional and only appropriate for a portfolio demonstration.

## Deploy to Vercel

1. Push this repository to GitHub.
2. Import the repository in Vercel.
3. Accept the detected Next.js defaults.
4. Deploy—no environment variables are required.

For CLI deployment, after authenticating with Vercel:

```bash
npx vercel
npx vercel --prod
```

## Simulated integrations

The staff assignment, handoff queue, ticketing, CRM pipeline and internal notes are browser-local simulations. They do not send email, WhatsApp, invoices or messages to a real team. All names and contact details are fictional.

## Production extensions

- Store conversations and leads in Postgres or a CRM such as HubSpot/Salesforce.
- Use verified server-side model calls with retrieval over approved company content.
- Connect WhatsApp Business and transactional email through server-side providers.
- Add role-based access, SSO, audit trails and consent/retention controls.
- Stream live conversations to agents and measure response SLAs.

## Limitations and next steps

This build intentionally favours predictable rules over open-ended generation, browser storage over a shared database, and demo identity over secure authentication. Production hardening would require company-approved content, privacy review, monitoring, human escalation SLAs, abuse protection and multilingual quality testing.
