"use client";

import { DepartmentChart, FunnelChart } from "@/components/charts";
import { PageHeading } from "@/components/dashboard-shell";
import { useDemo } from "@/components/demo-provider";

export default function AnalyticsPage() {
  const { conversations, leads } = useDemo();
  const departmentData = Object.entries(conversations.reduce<Record<string, number>>((a, c) => ({ ...a, [c.department]: (a[c.department] || 0) + 1 }), {})).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  const stages = ["New", "Qualified", "Contacted", "Consultation booked", "Proposal sent", "Converted"];
  const funnelData = stages.map((name, i) => ({ name, value: leads.filter(l => stages.indexOf(l.stage) >= i).length }));
  const destinations = Object.entries(leads.reduce<Record<string, number>>((a, l) => ({ ...a, [l.destination]: (a[l.destination] || 0) + 1 }), {})).sort((a, b) => b[1] - a[1]);
  const maxDestination = Math.max(...destinations.map(d => d[1]), 1);
  const topics = [{ name: "Destination & venue", value: 34 }, { name: "Budget guidance", value: 25 }, { name: "Availability & dates", value: 18 }, { name: "Careers", value: 13 }, { name: "Vendor partnerships", value: 10 }];
  const guests = leads.reduce((s, l) => s + l.guests, 0);

  return <div className="mx-auto max-w-[1320px]">
    <PageHeading eyebrow="Insight" title="Signals behind the conversations." copy="The questions, destinations and routes shaping demand." />

    <section className="mb-6 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-hairline bg-hairline lg:grid-cols-4">
      {[["Leads in pipeline", leads.length], ["Guests represented", guests.toLocaleString("en-IN")], ["Avg. fit score", `${Math.round(leads.reduce((s, l) => s + l.score, 0) / Math.max(leads.length, 1))}%`], ["Departments routed", departmentData.length]].map(([label, value]) =>
        <div key={label} className="bg-paper p-6"><p className="text-[11px] uppercase tracking-[.2em] text-charcoal/55">{label}</p><p className="mt-3 font-serif text-[40px] font-light leading-none text-ink">{value}</p></div>)}
    </section>

    <div className="grid gap-6 lg:grid-cols-2">
      <article className="panel p-7"><p className="eyebrow text-gold">Conversation routing</p><h2 className="mt-2 font-serif text-[28px] text-ink">Conversations by department</h2><DepartmentChart data={departmentData} /></article>
      <article className="panel p-7"><p className="eyebrow text-gold">Lead progression</p><h2 className="mt-2 font-serif text-[28px] text-ink">Lead funnel</h2><FunnelChart data={funnelData} />
        <p className="mt-6 border-t border-hairline pt-4 text-[12px] leading-5 text-charcoal/55">Counts leads at or beyond each stage; percentages show progression from the previous stage.</p></article>
      <article className="panel p-7"><p className="eyebrow text-gold">Demand map</p><h2 className="mt-2 font-serif text-[28px] text-ink">Popular destinations</h2>
        <div className="mt-7 space-y-5">{destinations.map(([name, value]) => <div key={name}>
          <div className="mb-2 flex justify-between text-[14px]"><span className="text-ink">{name}</span><span className="text-charcoal/50">{value} lead{value !== 1 ? "s" : ""}</span></div>
          <div className="h-1.5 overflow-hidden rounded-full bg-[#EFE8DC]"><div className="h-full rounded-full bg-gold" style={{ width: `${value / maxDestination * 100}%` }} /></div>
        </div>)}</div></article>
      <article className="panel p-7"><p className="eyebrow text-gold">What visitors ask</p><h2 className="mt-2 font-serif text-[28px] text-ink">Frequently asked topics</h2>
        <ol className="mt-5 divide-y divide-hairline">{topics.map((t, i) => <li key={t.name} className="flex items-center gap-5 py-3.5">
          <span className="w-6 font-serif text-xl italic text-gold">{i + 1}</span><span className="flex-1 text-[14px] text-ink">{t.name}</span><span className="text-[13px] tabular-nums text-charcoal/55">{t.value}%</span>
        </li>)}</ol>
        <p className="mt-3 text-[12px] text-charcoal/45">Illustrative sample distribution.</p></article>
    </div>
  </div>;
}
