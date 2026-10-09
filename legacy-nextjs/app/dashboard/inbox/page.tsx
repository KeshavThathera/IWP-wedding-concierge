"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Check, Send, Sparkles, UserCheck } from "lucide-react";
import { PageHeading } from "@/components/dashboard-shell";
import { useDemo } from "@/components/demo-provider";
import { Monogram } from "@/components/brand";
import { ConversationStatus } from "@/lib/types";

const statusTone: Record<ConversationStatus, string> = { Open: "bg-emerald-500", Waiting: "bg-gold", Resolved: "bg-charcoal/25" };
const select = "rounded-md border border-hairline bg-paper px-3 py-2.5 text-[13px] text-ink outline-none focus:border-gold";

export default function InboxPage() {
  const { conversations, updateConversation } = useDemo();
  const [selectedId, setSelectedId] = useState<string>();
  const [department, setDepartment] = useState("All");
  const [status, setStatus] = useState("All");
  const [note, setNote] = useState("");
  const [reply, setReply] = useState("");
  const [saved, setSaved] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  // Deep links from the overview use ?c=<conversation id>.
  useEffect(() => { const id = new URLSearchParams(window.location.search).get("c"); if (id) setSelectedId(id); }, []);

  const filtered = useMemo(() => conversations.filter(c => (department === "All" || c.department === department) && (status === "All" || c.status === status)), [conversations, department, status]);
  const selected = filtered.find(c => c.id === selectedId) || filtered[0];
  const departments = ["All", ...Array.from(new Set(conversations.map(c => c.department)))];

  useEffect(() => { setNote(selected?.note || ""); setReply(""); setSaved(false); }, [selected?.id, selected?.note]);
  useEffect(() => { threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" }); }, [selected?.id, selected?.transcript.length]);

  const sendReply = (e: FormEvent) => {
    e.preventDefault();
    if (!selected || !reply.trim()) return;
    const message = { id: crypto.randomUUID(), role: "agent" as const, text: reply.trim(), at: "Just now" };
    updateConversation(selected.id, { transcript: [...selected.transcript, message], status: "Waiting", updatedAt: "Just now" });
    setReply("");
  };

  return <div className="mx-auto max-w-[1480px]">
    <PageHeading eyebrow="Team inbox" title="One inbox, every enquiry." copy="Review context, take ownership and keep each handoff moving."
      action={<div className="flex gap-2">
        <select aria-label="Filter by department" value={department} onChange={e => setDepartment(e.target.value)} className={select}>{departments.map(x => <option key={x} value={x}>{x === "All" ? "All departments" : x}</option>)}</select>
        <select aria-label="Filter by status" value={status} onChange={e => setStatus(e.target.value)} className={select}>{["All", "Open", "Waiting", "Resolved"].map(x => <option key={x} value={x}>{x === "All" ? "All statuses" : x}</option>)}</select>
      </div>} />

    <div className="panel grid overflow-hidden lg:h-[calc(100dvh-240px)] lg:min-h-[640px] lg:grid-cols-[320px_1fr_300px]">
      {/* Conversation list */}
      <div className="flex min-h-0 flex-col border-b border-hairline lg:border-b-0 lg:border-r">
        <div className="border-b border-hairline px-5 py-4 text-[11px] uppercase tracking-[.2em] text-charcoal/50">{filtered.length} conversation{filtered.length !== 1 ? "s" : ""}</div>
        <div className="scrollbar-thin max-h-[360px] flex-1 overflow-y-auto lg:max-h-none">
          {filtered.map(c => <button key={c.id} onClick={() => setSelectedId(c.id)} className={`relative w-full border-b border-hairline px-5 py-4 text-left transition ${selected?.id === c.id ? "bg-ivory" : "hover:bg-ivory/50"}`}>
            {selected?.id === c.id && <span className="absolute inset-y-0 left-0 w-[2px] bg-burgundy" />}
            <div className="flex items-center justify-between gap-2"><span className="flex items-center gap-2 truncate text-[14px] font-medium text-ink"><span className={`h-1.5 w-1.5 shrink-0 rounded-full ${statusTone[c.status]}`} />{c.customer}</span><span className="shrink-0 text-[11px] text-charcoal/45">{c.updatedAt}</span></div>
            <p className="mt-1 truncate text-[13px] text-charcoal/55">{c.latest}</p>
            <div className="mt-2.5 flex items-center gap-2"><span className="text-[11px] uppercase tracking-[.12em] text-gold">{c.department}</span>{c.priority === "High" && <span className="rounded-full bg-burgundy/[.08] px-2 py-0.5 text-[10px] uppercase tracking-wider text-burgundy">Priority</span>}</div>
          </button>)}
        </div>
      </div>

      {selected ? <>
        {/* Thread */}
        <div className="flex min-h-[520px] min-w-0 flex-col border-b border-hairline lg:min-h-0 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between border-b border-hairline px-6 py-4">
            <div><p className="font-serif text-2xl text-ink">{selected.customer}</p><p className="text-[12px] text-charcoal/50">{selected.ticket} · {selected.department}</p></div>
            <span className="flex items-center gap-2 rounded-full border border-hairline px-3 py-1 text-[12px] text-charcoal/70"><span className={`h-1.5 w-1.5 rounded-full ${statusTone[selected.status]}`} />{selected.status}</span>
          </div>
          <div ref={threadRef} className="scrollbar-thin flex-1 space-y-4 overflow-y-auto bg-ivory/40 px-6 py-6">
            {selected.transcript.map(m => m.role === "visitor"
              ? <div key={m.id} className="flex justify-start"><div className="max-w-[78%] rounded-2xl rounded-tl-sm border border-hairline bg-paper px-4 py-3 text-[14px] leading-relaxed text-charcoal">{m.text}<p className="mt-1.5 text-[11px] text-charcoal/40">{selected.customer} · {m.at}</p></div></div>
              : <div key={m.id} className="flex justify-end"><div className={`max-w-[78%] rounded-2xl rounded-tr-sm px-4 py-3 text-[14px] leading-relaxed ${m.role === "agent" ? "bg-burgundy text-paper" : "bg-ink text-paper"}`}>
                  {m.text}
                  <p className="mt-1.5 flex items-center justify-end gap-1.5 text-[11px] text-paper/55">{m.role === "agent" ? <>Demo Manager</> : <><Monogram className="h-3 w-3 text-champagne" />Concierge</>} · {m.at}</p>
                </div></div>)}
          </div>
          <div className="border-t border-hairline p-4">
            {selected.assignedTo
              ? <form onSubmit={sendReply} className="flex items-center gap-2 rounded-full border border-hairline bg-paper py-1.5 pl-5 pr-1.5 focus-within:border-gold">
                  <input value={reply} onChange={e => setReply(e.target.value)} placeholder={`Reply to ${selected.customer}…`} aria-label="Reply" className="min-w-0 flex-1 bg-transparent py-2 text-[14px] outline-none placeholder:text-charcoal/40" />
                  <button disabled={!reply.trim()} aria-label="Send reply" className="grid h-10 w-10 place-items-center rounded-full bg-ink text-paper transition hover:bg-burgundy disabled:opacity-30"><Send size={16} /></button>
                </form>
              : <div className="flex items-center justify-between gap-3 rounded-md border border-dashed border-hairline px-4 py-3 text-[13px] text-charcoal/55"><span className="flex items-center gap-2"><UserCheck size={15} />Take over this conversation to reply.</span>
                  <button onClick={() => updateConversation(selected.id, { assignedTo: "Demo Manager", status: "Open" })} className="text-[12px] uppercase tracking-[.14em] text-burgundy hover:text-ink">Take over</button></div>}
          </div>
        </div>

        {/* Context */}
        <aside className="scrollbar-thin min-h-0 overflow-y-auto p-6">
          <div className="rounded-md border border-gold/30 bg-ivory/60 p-4">
            <p className="flex items-center gap-2 text-[11px] uppercase tracking-[.18em] text-gold"><Sparkles size={13} />Concierge summary</p>
            <p className="mt-3 text-[14px] leading-6 text-charcoal/80">{selected.summary}</p>
          </div>
          <p className="mt-7 text-[11px] uppercase tracking-[.2em] text-charcoal/50">Owner</p>
          <button onClick={() => updateConversation(selected.id, { assignedTo: selected.assignedTo ? undefined : "Demo Manager" })} className="mt-3 flex w-full items-center justify-between rounded-md border border-hairline p-3 text-left transition hover:border-gold">
            <span><span className="block text-[14px] text-ink">{selected.assignedTo || "Unassigned"}</span><span className="text-[12px] text-charcoal/50">{selected.assignedTo ? "Click to release" : "Click to assign yourself"}</span></span>
            {selected.assignedTo ? <Check size={16} className="text-sage" /> : <UserCheck size={16} className="text-burgundy" />}
          </button>
          <p className="mt-7 text-[11px] uppercase tracking-[.2em] text-charcoal/50">Status</p>
          <div className="mt-3 grid grid-cols-3 gap-1 rounded-md bg-linen/70 p-1">{(["Open", "Waiting", "Resolved"] as ConversationStatus[]).map(x =>
            <button key={x} onClick={() => updateConversation(selected.id, { status: x })} className={`rounded py-2 text-[12px] transition ${selected.status === x ? "bg-paper text-ink shadow-card" : "text-charcoal/55 hover:text-ink"}`}>{x}</button>)}</div>
          <p className="mt-7 text-[11px] uppercase tracking-[.2em] text-charcoal/50">Internal note</p>
          <textarea value={note} onChange={e => { setNote(e.target.value); setSaved(false); }} placeholder="Add context for the team…" className="mt-3 h-28 w-full resize-none rounded-md border border-hairline bg-paper p-3 text-[13px] leading-5 outline-none focus:border-gold" />
          <button onClick={() => { updateConversation(selected.id, { note }); setSaved(true); }} className="btn-outline mt-2 w-full py-3">{saved ? <><Check size={14} />Saved</> : "Save note"}</button>
          <p className="mt-6 text-center text-[11px] text-charcoal/40">Demo workspace · no message leaves this browser</p>
        </aside>
      </> : <div className="col-span-2 grid place-items-center p-16 text-[14px] text-charcoal/50">No conversations match these filters.</div>}
    </div>
  </div>;
}
