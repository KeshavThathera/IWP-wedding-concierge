"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ArrowUpRight, Send, X } from "lucide-react";
import { useDemo } from "./demo-provider";
import { Monogram } from "./brand";
import { Conversation, Department, Lead, Message } from "@/lib/types";

const ASK_EVENT = "iwp:ask-concierge";
/** Opens the concierge from anywhere on the page, optionally sending a first message. */
export function askConcierge(prompt?: string) {
  window.dispatchEvent(new CustomEvent(ASK_EVENT, { detail: prompt }));
}

const opening = "Namaste, and welcome. I’m the IWP wedding concierge. I can help you explore destinations, begin planning your celebration or reach the right member of our team. How may I help?";
const quickActions = ["Plan my wedding", "Explore venues", "Understand budgets", "Careers", "Vendor collaboration", "Existing client support", "Speak to a person"];

type Lang = "en" | "hi";
type Slot = "destination" | "guests" | "date" | "budget" | "style" | "contact";
const slotOrder: Slot[] = ["destination", "guests", "date", "budget", "style", "contact"];
const slotDetectors: Record<Slot, RegExp> = {
  destination: /jaipur|udaipur|goa|jodhpur|kerala|mussoorie|jim corbett|abroad|thailand|bali|dubai/i,
  guests: /\d{2,4}\s*(?:guests?|people|log|pax|mehmaan)/i,
  date: /january|february|march|april|may|june|july|august|september|october|november|december|winter|summer|monsoon|\b20\d\d\b/i,
  budget: /₹|\brs\.?|\binr\b|lakh|crore|\bcr\b|no limit/i,
  style: /palace|fort|beach|lake|resort|heritage|haveli/i,
  contact: /@|\+?\d[\d\s-]{8,}|whatsapp|phone|email|call/i
};
const questions: Record<Lang, Record<Slot, string>> = {
  en: {
    destination: "How lovely. Is there a destination—or a kind of setting—you find yourselves drawn to?",
    guests: "Approximately how many guests are you hoping to welcome?",
    date: "Which month or season are you considering for the celebration?",
    budget: "Do you have a comfortable budget range in mind? An approximate figure is perfectly fine.",
    style: "Which setting feels most like you: a palace, a fort, a lakeside terrace, a beach or a resort?",
    contact: "Finally, how would you prefer our planners reach you—phone, WhatsApp or email?"
  },
  hi: {
    destination: "Bahut sundar! Aap kis destination ya kis tarah ki setting ke baare mein soch rahe hain?",
    guests: "Lagbhag kitne mehmaan aane ki ummeed hai?",
    date: "Shaadi ke liye kaun sa mahina ya season soch rahe hain?",
    budget: "Kya aapke mann mein koi budget range hai? Andaaza bhi kaafi hai.",
    style: "Aapko kaun si setting sabse zyada pasand hai: palace, fort, lakeside, beach ya resort?",
    contact: "Aakhir mein, hamare planners aapse kaise sampark karein—phone, WhatsApp ya email?"
  }
};
const destinationIntros: Record<string, string> = {
  jaipur: "Jaipur is extraordinary for heritage-palace celebrations—courtyards, mirrored halls and a truly royal scale.",
  udaipur: "Udaipur is made for lakeside grandeur—sunset terraces, palace views across the water and an intimate elegance.",
  jodhpur: "Jodhpur brings drama: fort ramparts, desert evenings and the blue city glowing below.",
  goa: "Goa suits relaxed, barefoot celebrations—sunlit beaches and multi-day festivities by the sea.",
  kerala: "Kerala offers serene backwater and coastal settings, lush and wonderfully calm."
};

const humanRequest = /human|person|someone|team member|इंसान|baat karni|kisi se baat/i;
const affirmative = /^(yes|yeah|yep|sure|ok|okay|please|haan|ha|ji|haanji|zaroor|bilkul|go ahead|do it)\b/i;
const negative = /^(no|nope|not now|nahi|nahin|later)\b/i;

function detectLang(text: string): Lang {
  return /[ऀ-ॿ]|\b(main|mein|hai|hoon|kar raha|kar rahi|shaadi|chahiye|kya|aap|nahi|haan|hum)\b/i.test(text) ? "hi" : "en";
}

function detectDepartment(text: string, current?: Department): Department {
  const t = text.toLowerCase();
  if (/job|career|intern|apply|resume|\bcv\b|नौकरी|naukri/.test(t)) return "HR and Careers";
  if (/photograph|vendor|collaborat|partner|decor|supplier/.test(t)) return "Vendors and Partnerships";
  if (/invoice|payment|refund|finance|\bbill/.test(t)) return "Finance";
  if (/already.*client|existing client|urgent help|booking support|मेरी बुकिंग/.test(t)) return "Client Servicing";
  if (/press|media|marketing|influencer|\bpr\b/.test(t)) return "Marketing and PR";
  if (/wedding|venue|jaipur|udaipur|goa|jodhpur|kerala|guest|budget|plan my|शादी|shaadi/.test(t)) return "Wedding Sales";
  return current || "General Support";
}

const departmentOpeners: Partial<Record<Department, string>> = {
  "HR and Careers": "Thank you for your interest in joining us. I’ve noted this for our HR and Careers team. What email address should they use to reach you?",
  "Vendors and Partnerships": "How lovely—we always enjoy meeting new creative partners. Could you share your name or studio name, along with a contact email?",
  "Client Servicing": "I understand this may be time-sensitive, and I’ve marked it as a priority for Client Servicing. Shall I connect you with a team member now?",
  Finance: "Of course. I’ve routed this to our Finance team. Please share your name and the email linked to your booking—no card or bank details, please.",
  "Marketing and PR": "Thank you for reaching out. I’ve noted this for Marketing and PR. Could you share your publication or brand, and a contact email?"
};

type Flow = { asked: Slot[]; answers: Partial<Record<Slot, string>>; offered: boolean; contactAsked: boolean };
const freshFlow = (): Flow => ({ asked: [], answers: {}, offered: false, contactAsked: false });

/** Decides the next reply. Returns null when the visitor should be handed to a person. */
function respond(text: string, dept: Department, flow: Flow, lang: Lang): { reply: string | null; flow: Flow } {
  const next: Flow = { ...flow, asked: [...flow.asked], answers: { ...flow.answers } };
  if (humanRequest.test(text)) return { reply: null, flow: next };
  if (flow.offered && affirmative.test(text.trim())) return { reply: null, flow: next };
  if (flow.offered && negative.test(text.trim())) {
    next.offered = false;
    return { reply: lang === "hi" ? "Bilkul, koi jaldi nahi. Main aur kis tarah madad kar sakta hoon?" : "Of course—there’s no rush. Is there anything else you’d like to explore?", flow: next };
  }

  if (dept === "Wedding Sales") {
    // The latest reply answers whatever was asked last; regexes catch details volunteered early.
    const lastAsked = flow.asked[flow.asked.length - 1];
    if (lastAsked && !next.answers[lastAsked]) next.answers[lastAsked] = text;
    for (const slot of slotOrder) if (!next.answers[slot] && slotDetectors[slot].test(text)) next.answers[slot] = text;
    const pending = slotOrder.find(s => !next.answers[s]);
    const city = Object.keys(destinationIntros).find(c => new RegExp(c, "i").test(text) && !flow.answers.destination);
    const intro = !city ? "" : lang === "hi" ? `${titleCase(city)} ek behtareen choice hai! ` : destinationIntros[city] + " ";
    if (/budget|बजट/i.test(text) && !flow.asked.includes("budget") && flow.asked.length === 0) {
      next.asked.push("guests");
      return { reply: "A meaningful estimate depends on guest count, destination, venue exclusivity and the number of events. Shall we begin with how many guests you’re expecting?", flow: next };
    }
    if (pending) {
      next.asked.push(pending);
      return { reply: intro + questions[lang][pending], flow: next };
    }
    next.offered = true;
    return { reply: lang === "hi" ? "Shukriya! Ek planner ke liye zaroori sab kuch mil gaya hai. Kya main aapko hamari Wedding Sales team se jod doon?" : "Thank you—that’s everything a planner needs to begin. Shall I introduce you to our Wedding Sales team?", flow: next };
  }

  const opener = departmentOpeners[dept];
  if (opener && !flow.contactAsked) {
    next.contactAsked = true;
    if (dept === "Client Servicing") next.offered = true;
    return { reply: opener, flow: next };
  }
  if (opener) {
    next.offered = true;
    return { reply: `Thank you, that’s noted. Shall I pass this conversation to our ${dept} team now?`, flow: next };
  }
  if (lang === "hi") return { reply: "बिल्कुल। मैं हिंदी या Hinglish में आपकी मदद कर सकता हूँ। क्या आप शादी की planning कर रहे हैं, venue देखना चाहते हैं, या team से बात करना चाहते हैं?", flow: next };
  return { reply: "I can help with wedding planning, destinations, careers, vendor partnerships, client support or finance. Which would you like to explore?", flow: next };
}

const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();

export function ConciergeChat() {
  const { addConversation, addLead } = useDemo();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{ id: "welcome", role: "assistant", text: opening, at: "Now" }]);
  const [input, setInput] = useState("");
  const [department, setDepartment] = useState<Department>("General Support");
  const [flow, setFlow] = useState<Flow>(freshFlow);
  const [typing, setTyping] = useState(false);
  const [ticket, setTicket] = useState<string>();
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, open, typing]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    inputRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const handoff = useCallback((dept: Department, transcript: Message[], answers: Flow["answers"]) => {
    const reference = `IWP-${1042 + Math.floor(Math.random() * 700)}`;
    const confirmation = `Thank you. I’ve prepared this conversation for our ${dept} team, who will take it from here. Your reference is ${reference}.`;
    const finalMessages = [...transcript, { id: crypto.randomUUID(), role: "assistant" as const, text: confirmation, at: "Now" }];
    setTicket(reference); setMessages(finalMessages);
    const visitorText = transcript.filter(m => m.role === "visitor").map(m => m.text).join(" ");
    const latestVisitor = [...transcript].reverse().find(m => m.role === "visitor")?.text || "Requested assistance";

    const destination = visitorText.match(slotDetectors.destination)?.[0];
    const guests = (answers.guests || visitorText).match(/(\d{2,4})/)?.[1];
    const budget = answers.budget?.trim() || visitorText.match(/(?:₹|rs\.?|inr)\s*[\d.]+\s*(?:[-–]\s*[\d.]+)?\s*(?:cr|crore|l|lakh)?/i)?.[0];
    const month = (answers.date || visitorText).match(slotDetectors.date)?.[0];
    const style = (answers.style || visitorText).match(slotDetectors.style)?.[0];
    const contact = (answers.contact || "").match(/[\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d\s-]{8,}\d/)?.[0];
    const contactMethod = (answers.contact || "").match(/whatsapp|phone|email|call/i)?.[0];
    const details = [destination && titleCase(destination), guests && `${guests} guests`, month && titleCase(month), budget, style && titleCase(style)].filter(Boolean).join(" · ");
    const summary = dept === "Wedding Sales" && details
      ? `Wedding enquiry from the website concierge: ${details}. Visitor asked to be introduced to a planner.`
      : `New ${dept.toLowerCase()} enquiry from the website concierge. Visitor requested a human handoff.`;

    const conversation: Conversation = { id: crypto.randomUUID(), ticket: reference, customer: "Website visitor", department: dept, status: "Open", priority: dept === "Client Servicing" ? "High" : "Medium", latest: latestVisitor, summary, updatedAt: "Just now", transcript: finalMessages };
    addConversation(conversation);
    if (dept === "Wedding Sales" && (destination || guests || budget)) {
      const complete = Boolean(destination && guests && budget);
      const lead: Lead = { id: crypto.randomUUID(), name: "Website visitor", contact: contact || "To be collected", destination: destination ? titleCase(destination) : "To be decided", guests: Number(guests || 0), budget: budget || "To be discussed", date: month ? `${titleCase(month)} (year TBD)` : "Flexible", venueStyle: style ? titleCase(style) : "To be discussed", contactMethod: contactMethod ? titleCase(contactMethod) : "To be collected", stage: complete ? "Qualified" : "New", score: complete ? 86 : 62, createdAt: "Just now" };
      addLead(lead);
    }
  }, [addConversation, addLead]);

  const submit = useCallback((raw: string) => {
    const text = raw.trim();
    if (!text || ticket || typing) return;
    const visitor: Message = { id: crypto.randomUUID(), role: "visitor", text, at: "Now" };
    // Once a visitor writes in Hindi or Hinglish, keep replying that way.
    const lang = detectLang([...messages.filter(m => m.role === "visitor").map(m => m.text), text].join(" "));
    const nextDepartment = detectDepartment(text, department === "General Support" ? undefined : department);
    const transcript = [...messages, visitor];
    const { reply, flow: nextFlow } = respond(text, nextDepartment, nextDepartment === department ? flow : { ...freshFlow(), offered: flow.offered }, lang);
    setDepartment(nextDepartment); setFlow(nextFlow); setInput(""); setMessages(transcript); setTyping(true);
    window.setTimeout(() => {
      setTyping(false);
      if (reply === null) handoff(nextDepartment, transcript, nextFlow.answers);
      else setMessages([...transcript, { id: crypto.randomUUID(), role: "assistant", text: reply, at: "Now" }]);
    }, 650 + Math.min(reply?.length ?? 80, 160) * 4);
  }, [department, flow, handoff, messages, ticket, typing]);

  // Let buttons elsewhere on the page open the concierge with a prompt.
  const submitRef = useRef(submit);
  useEffect(() => { submitRef.current = submit; }, [submit]);
  useEffect(() => {
    const onAsk = (e: Event) => {
      setOpen(true);
      const prompt = (e as CustomEvent<string | undefined>).detail;
      if (prompt) window.setTimeout(() => submitRef.current(prompt), 250);
    };
    window.addEventListener(ASK_EVENT, onAsk);
    return () => window.removeEventListener(ASK_EVENT, onAsk);
  }, []);

  const restart = () => { setTicket(undefined); setFlow(freshFlow()); setDepartment("General Support"); setMessages([{ id: crypto.randomUUID(), role: "assistant", text: opening, at: "Now" }]); };
  const onSubmit = (e: FormEvent) => { e.preventDefault(); submit(input); };

  return (
    <>
      <button onClick={() => setOpen(true)} aria-label="Open the wedding concierge" className={`group fixed bottom-6 right-6 z-40 flex items-center gap-3 rounded-full bg-ink p-2.5 text-paper sm:pr-6 shadow-soft ring-1 ring-champagne/30 transition duration-300 hover:-translate-y-0.5 hover:bg-burgundy ${open ? "pointer-events-none translate-y-2 opacity-0" : ""}`}>
        <span className="relative grid h-10 w-10 place-items-center rounded-full border border-champagne/40">
          <Monogram className="h-6 w-6 text-champagne" />
          <span className="absolute right-0 top-0 h-2.5 w-2.5 rounded-full border-2 border-ink bg-emerald-400" />
        </span>
        <span className="hidden text-left leading-tight sm:block">
          <span className="block font-serif text-lg">Concierge</span>
          <span className="block text-[10px] uppercase tracking-wide2 text-paper/60">Ask us anything</span>
        </span>
      </button>

      {open && <div className="fixed inset-0 z-50 flex animate-fade-in items-end justify-end bg-ink/30 backdrop-blur-[2px] sm:p-6" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
        <section role="dialog" aria-modal="true" aria-label="IWP wedding concierge" className="flex h-[94dvh] w-full animate-rise-in flex-col overflow-hidden bg-paper shadow-soft sm:h-[720px] sm:max-h-[calc(100dvh-3rem)] sm:max-w-[430px] sm:rounded-xl">
          <header className="relative bg-ink px-6 pb-5 pt-6 text-paper">
            <button onClick={() => setOpen(false)} aria-label="Close concierge" className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full text-paper/70 transition hover:bg-paper/10 hover:text-paper"><X size={18} /></button>
            <div className="relative flex items-center gap-4">
              <span className="grid h-12 w-12 place-items-center rounded-full border border-champagne/40"><Monogram className="h-7 w-7 text-champagne" /></span>
              <div>
                <h2 className="font-serif text-[26px] font-normal leading-none">The Concierge</h2>
                <p className="mt-1.5 flex items-center gap-2 text-[11px] text-paper/60"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />Online · English, हिन्दी, Hinglish</p>
              </div>
            </div>
            <div className="relative mt-5 flex items-center justify-between border-t border-paper/15 pt-4 text-[10px] uppercase tracking-wide2">
              <span className="text-paper/50">Routing to</span>
              <span key={department} className="animate-fade-in text-champagne">{department}</span>
            </div>
          </header>

          <div ref={scrollRef} className="scrollbar-thin flex-1 space-y-5 overflow-y-auto bg-ivory/40 px-5 py-6">
            {messages.map(message => message.role === "assistant"
              ? <div key={message.id} className="flex animate-rise-in gap-3">
                  <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full border border-gold/30 bg-paper"><Monogram className="h-4 w-4 text-gold" /></span>
                  <div className="max-w-[84%] rounded-2xl rounded-tl-sm border border-hairline bg-paper px-4 py-3 text-[14px] leading-relaxed text-charcoal shadow-card">{message.text}</div>
                </div>
              : <div key={message.id} className="flex animate-rise-in justify-end">
                  <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-burgundy px-4 py-3 text-[14px] leading-relaxed text-paper">{message.text}</div>
                </div>)}
            {typing && <div className="flex gap-3" aria-live="polite" aria-label="Concierge is typing">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-gold/30 bg-paper"><Monogram className="h-4 w-4 text-gold" /></span>
              <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-hairline bg-paper px-4 py-4">
                {[0, 1, 2].map(i => <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-gold/70" style={{ animationDelay: `${i * 140}ms` }} />)}
              </div>
            </div>}
            {messages.length === 1 && !typing && <div className="flex flex-wrap gap-2 pl-11">
              {quickActions.map(action => <button key={action} onClick={() => submit(action)} className="rounded-full border border-ink/15 bg-paper px-3.5 py-2 text-[12px] text-charcoal transition hover:border-burgundy hover:bg-burgundy hover:text-paper">{action}</button>)}
            </div>}
            {ticket && <div className="ml-11 animate-rise-in rounded-lg border border-gold/40 bg-paper p-4">
              <p className="eyebrow text-gold">Handoff prepared</p>
              <p className="mt-2 font-serif text-2xl text-ink">{ticket}</p>
              <p className="mt-1 text-[12px] text-charcoal/60">{department} · simulated for this demo</p>
              <Link href="/dashboard/inbox" className="mt-3 inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide2 text-burgundy hover:text-ink">View in staff inbox <ArrowUpRight size={13} /></Link>
            </div>}
          </div>

          <footer className="border-t border-hairline bg-paper p-4">
            {ticket
              ? <button onClick={restart} className="btn-dark w-full">Start a new conversation</button>
              : <form onSubmit={onSubmit} className="flex items-center gap-2 rounded-full border border-hairline bg-ivory/50 py-1.5 pl-5 pr-1.5 transition focus-within:border-gold focus-within:bg-paper">
                  <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} className="min-w-0 flex-1 bg-transparent py-2 text-[14px] outline-none placeholder:text-charcoal/40" placeholder="Write in English, हिन्दी or Hinglish…" aria-label="Message" />
                  <button disabled={!input.trim() || typing} className="grid h-10 w-10 place-items-center rounded-full bg-ink text-paper transition hover:bg-burgundy disabled:opacity-30" aria-label="Send message"><Send size={16} /></button>
                </form>}
            <p className="mt-3 text-center text-[10px] uppercase tracking-wide2 text-charcoal/40">Independent concept demo · no live team connected</p>
          </footer>
        </section>
      </div>}
    </>
  );
}
