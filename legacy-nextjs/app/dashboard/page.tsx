"use client";

import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { DepartmentChart } from "@/components/charts";
import { PageHeading } from "@/components/dashboard-shell";
import { useDemo } from "@/components/demo-provider";

const initials = (name: string) => name.split(/\s|&/).filter(Boolean).slice(0, 2).map(w => w[0]).join("").toUpperCase();

export default function DashboardOverview() {
  const { conversations, leads } = useDemo();
  const open = conversations.filter(c => c.status === "Open").length;
  const priority = conversations.filter(c => c.priority === "High" && c.status !== "Resolved").length;
  const qualified = leads.filter(l => l.stage !== "New").length;
  const converted = leads.filter(l => l.stage === "Converted").length;
  const cards = [
    { label: "Conversations", value: conversations.length, note: `${open} open right now` },
    { label: "Qualified leads", value: qualified, note: `${Math.round(qualified / Math.max(leads.length, 1) * 100)}% of all leads` },
    { label: "Needs attention", value: priority, note: "High-priority, unresolved" },
    { label: "Celebrations won", value: converted, note: `${leads.length} in the pipeline` }
  ];
  const departmentData = Object.entries(conversations.reduce<Record<string, number>>((a, c) => ({ ...a, [c.department]: (a[c.department] || 0) + 1 }), {})).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  const topLeads = [...leads].filter(l => l.stage !== "Converted").sort((a, b) => b.score - a.score).slice(0, 3);

  return <div className="mx-auto max-w-[1320px]">
    <PageHeading eyebrow="Thursday, 8 October 2026" title="Good morning, Demo Manager." copy="Here is what the concierge has prepared for your team today."
      action={<Link href="/dashboard/inbox" className="btn-dark self-start">Open team inbox <ArrowRight size={14} /></Link>} />

    <section className="grid gap-px overflow-hidden rounded-lg border border-hairline bg-hairline sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(c => <article key={c.label} className="bg-paper p-7">
        <p className="text-[11px] uppercase tracking-[.2em] text-charcoal/55">{c.label}</p>
        <p className="mt-4 font-serif text-[56px] font-light leading-none text-ink">{c.value}</p>
        <p className="mt-3 text-[13px] text-charcoal/55">{c.note}</p>
      </article>)}
    </section>

    <section className="mt-6 grid gap-6 xl:grid-cols-[1.25fr_.75fr]">
      <article className="panel p-7">
        <div className="flex items-end justify-between border-b border-hairline pb-5">
          <div><p className="eyebrow text-gold">Live queue</p><h2 className="mt-2 font-serif text-[28px] font-normal text-ink">Recent conversations</h2></div>
          <Link href="/dashboard/inbox" className="flex items-center gap-1.5 text-[12px] uppercase tracking-[.16em] text-burgundy hover:text-ink">View all <ArrowUpRight size={14} /></Link>
        </div>
        <div className="divide-y divide-hairline">
          {conversations.slice(0, 6).map(c => <Link href={`/dashboard/inbox?c=${c.id}`} key={c.id} className="-mx-3 flex items-center gap-4 rounded-md px-3 py-4 transition hover:bg-ivory/70">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-hairline bg-ivory font-serif text-[15px] text-burgundy">{initials(c.customer)}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2"><p className="truncate text-[14px] font-medium text-ink">{c.customer}</p>{c.priority === "High" && c.status !== "Resolved" && <span className="rounded-full bg-burgundy/[.08] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-burgundy">Priority</span>}</div>
              <p className="mt-0.5 truncate text-[13px] text-charcoal/55">{c.latest}</p>
            </div>
            <div className="hidden text-right sm:block"><p className="text-[12px] text-charcoal/75">{c.department}</p><p className="mt-0.5 text-[12px] text-charcoal/45">{c.updatedAt}</p></div>
          </Link>)}
        </div>
      </article>

      <div className="space-y-6">
        <article className="panel p-7">
          <p className="eyebrow text-gold">Routing mix</p>
          <h2 className="mt-2 font-serif text-[28px] font-normal text-ink">By department</h2>
          <DepartmentChart data={departmentData} />
        </article>
        <article className="panel p-7">
          <div className="flex items-end justify-between"><div><p className="eyebrow text-gold">Strongest fit</p><h2 className="mt-2 font-serif text-[28px] font-normal text-ink">Leads to call first</h2></div><Link href="/dashboard/leads" className="text-[12px] uppercase tracking-[.16em] text-burgundy hover:text-ink">Pipeline</Link></div>
          <ul className="mt-4 divide-y divide-hairline">
            {topLeads.map(l => <li key={l.id} className="flex items-center justify-between gap-4 py-3.5">
              <div className="min-w-0"><p className="truncate text-[14px] font-medium text-ink">{l.name}</p><p className="truncate text-[13px] text-charcoal/55">{l.destination} · {l.guests} guests · {l.budget}</p></div>
              <span className="shrink-0 font-serif text-2xl text-burgundy">{l.score}<span className="text-sm text-charcoal/40">%</span></span>
            </li>)}
          </ul>
        </article>
      </div>
    </section>
  </div>;
}
