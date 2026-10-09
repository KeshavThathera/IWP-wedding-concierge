"use client";

import { useState } from "react";

export const CHART_COLORS = ["#5E1224", "#A8834A", "#6F7D66", "#B9776A", "#7A6E64", "#D8C39A", "#2A211C"];

type Datum = { name: string; value: number };

/** Donut with an interactive legend; hovering a slice or a legend row highlights it. */
export function DepartmentChart({ data }: { data: Datum[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = 70, stroke = 18, c = 2 * Math.PI * r, gap = data.length > 1 ? 3 : 0;
  let offset = 0;
  const focus = hover === null ? null : data[hover];
  return <div className="mt-6 grid items-center gap-8 sm:grid-cols-[180px_1fr]">
    <div className="relative mx-auto h-[180px] w-[180px]">
      <svg viewBox="0 0 180 180" className="-rotate-90">
        <circle cx="90" cy="90" r={r} fill="none" stroke="#EFE8DC" strokeWidth={stroke} />
        {data.map((d, i) => {
          const len = (d.value / total) * c;
          const el = <circle key={d.name} cx="90" cy="90" r={r} fill="none" stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={hover === i ? stroke + 4 : stroke}
            strokeDasharray={`${Math.max(len - gap, 0.5)} ${c}`} strokeDashoffset={-offset} opacity={hover === null || hover === i ? 1 : .35}
            className="cursor-pointer transition-all duration-300" onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} />;
          offset += len;
          return el;
        })}
      </svg>
      <div className="pointer-events-none absolute inset-0 grid place-content-center text-center">
        <p className="font-serif text-4xl font-light text-ink">{focus ? focus.value : total}</p>
        <p className="mt-0.5 max-w-[100px] text-[10px] uppercase leading-4 tracking-[.16em] text-charcoal/50">{focus ? focus.name : "Conversations"}</p>
      </div>
    </div>
    <ul className="space-y-1">
      {data.map((d, i) => <li key={d.name} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} className={`flex items-center gap-3 rounded-md px-2 py-1.5 text-[13px] transition ${hover === i ? "bg-linen/70" : ""}`}>
        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
        <span className="flex-1 truncate text-charcoal/80">{d.name}</span>
        <span className="tabular-nums text-charcoal/50">{Math.round(d.value / total * 100)}%</span>
        <span className="w-6 text-right font-medium tabular-nums text-ink">{d.value}</span>
      </li>)}
    </ul>
  </div>;
}

/** Horizontal funnel: each stage's bar is scaled to the first stage. */
export function FunnelChart({ data }: { data: Datum[] }) {
  const max = Math.max(...data.map(d => d.value), 1);
  return <div className="mt-7 space-y-3">
    {data.map((d, i) => {
      const prev = i > 0 ? data[i - 1].value : null;
      return <div key={d.name} className="grid grid-cols-[140px_1fr_3rem] items-center gap-4">
        <span className="text-[13px] text-charcoal/75">{d.name}</span>
        <div className="h-7 overflow-hidden rounded-sm bg-[#EFE8DC]">
          <div className="flex h-full items-center justify-end rounded-sm pr-2 transition-all duration-700" style={{ width: `${Math.max(d.value / max * 100, 4)}%`, background: CHART_COLORS[0], opacity: 1 - i * .12 }} />
        </div>
        <span className="text-right text-[13px] tabular-nums text-ink">{d.value}{prev ? <span className="block text-[10px] text-charcoal/45">{Math.round(d.value / prev * 100)}%</span> : null}</span>
      </div>;
    })}
  </div>;
}
