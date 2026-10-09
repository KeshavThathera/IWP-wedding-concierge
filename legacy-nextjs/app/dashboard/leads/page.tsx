"use client";

import { useState } from "react";
import { CalendarDays, GripVertical, MapPin, Users } from "lucide-react";
import { PageHeading } from "@/components/dashboard-shell";
import { useDemo } from "@/components/demo-provider";
import { LeadStage } from "@/lib/types";

const stages: LeadStage[] = ["New", "Qualified", "Contacted", "Consultation booked", "Proposal sent", "Converted"];

export default function LeadsPage() {
  const { leads, moveLead } = useDemo();
  const [dragging, setDragging] = useState<string>();
  const [over, setOver] = useState<LeadStage>();

  return <div className="mx-auto max-w-[1680px]">
    <PageHeading eyebrow="Lead pipeline" title="From first hello to celebration." copy="Drag a lead between stages, or use its menu. Changes persist in this browser." />
    <div className="scrollbar-thin -mx-4 overflow-x-auto px-4 pb-4 sm:-mx-10 sm:px-10">
      <div className="grid min-w-[1440px] grid-cols-6 gap-4">
        {stages.map((stage, i) => {
          const stageLeads = leads.filter(l => l.stage === stage);
          return <section key={stage}
            onDragOver={e => { e.preventDefault(); setOver(stage); }}
            onDragLeave={() => setOver(o => (o === stage ? undefined : o))}
            onDrop={e => { e.preventDefault(); const id = e.dataTransfer.getData("text/plain"); if (id) moveLead(id, stage); setOver(undefined); setDragging(undefined); }}
            className={`flex min-h-[540px] flex-col rounded-lg border p-3 transition ${over === stage ? "border-gold bg-champagne/15" : "border-transparent bg-linen/60"}`}>
            <header className="mb-3 flex items-center justify-between border-b border-hairline px-1 pb-3">
              <div className="flex items-center gap-2"><span className="font-serif text-lg italic text-gold">{i + 1}</span><h2 className="text-[12px] uppercase tracking-[.14em] text-ink">{stage}</h2></div>
              <span className="text-[13px] tabular-nums text-charcoal/50">{stageLeads.length}</span>
            </header>
            <div className="flex-1 space-y-3">
              {stageLeads.map(lead => <article key={lead.id} draggable
                onDragStart={e => { e.dataTransfer.setData("text/plain", lead.id); e.dataTransfer.effectAllowed = "move"; setDragging(lead.id); }}
                onDragEnd={() => { setDragging(undefined); setOver(undefined); }}
                className={`group cursor-grab rounded-md border border-hairline bg-paper p-4 shadow-card transition hover:border-gold/50 active:cursor-grabbing ${dragging === lead.id ? "opacity-40" : ""}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0"><p className="truncate font-serif text-xl leading-tight text-ink">{lead.name}</p><p className="mt-0.5 truncate text-[12px] text-charcoal/50">{lead.contact}</p></div>
                  <GripVertical size={15} className="mt-1 shrink-0 text-charcoal/25 transition group-hover:text-charcoal/50" />
                </div>
                <div className="mt-4 space-y-1.5 text-[13px] text-charcoal/70">
                  <p className="flex items-center gap-2"><MapPin size={13} className="shrink-0 text-gold" /><span className="truncate">{lead.destination} · {lead.venueStyle}</span></p>
                  <p className="flex items-center gap-2"><Users size={13} className="shrink-0 text-gold" /><span className="truncate">{lead.guests || "—"} guests · {lead.budget}</span></p>
                  <p className="flex items-center gap-2"><CalendarDays size={13} className="shrink-0 text-gold" /><span className="truncate">{lead.date}</span></p>
                </div>
                <div className="mt-4 border-t border-hairline pt-3">
                  <div className="flex items-center justify-between text-[11px] uppercase tracking-[.12em] text-charcoal/50"><span>Fit</span><span className="text-ink">{lead.score}%</span></div>
                  <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-linen"><div className="h-full rounded-full bg-gold" style={{ width: `${lead.score}%` }} /></div>
                  <select aria-label={`Move ${lead.name}`} value={lead.stage} onChange={e => moveLead(lead.id, e.target.value as LeadStage)} className="mt-3 w-full rounded border border-hairline bg-ivory/50 px-2 py-1.5 text-[12px] text-ink outline-none focus:border-gold">
                    {stages.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </article>)}
              {stageLeads.length === 0 && <div className="grid h-28 place-items-center rounded-md border border-dashed border-charcoal/15 text-[12px] text-charcoal/40">Drop a lead here</div>}
            </div>
          </section>;
        })}
      </div>
    </div>
  </div>;
}
