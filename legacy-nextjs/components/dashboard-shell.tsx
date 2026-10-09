"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, BarChart3, Inbox, LayoutDashboard, Menu, RotateCcw, UsersRound, X } from "lucide-react";
import { useState } from "react";
import { Brand } from "./brand";
import { useDemo } from "./demo-provider";

const links = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/inbox", label: "Team inbox", icon: Inbox },
  { href: "/dashboard/leads", label: "Lead pipeline", icon: UsersRound },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 }
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const path = usePathname(); const [open, setOpen] = useState(false); const { conversations, resetDemo } = useDemo();
  const active = links.find(l => l.href === path)?.label || "Workspace";
  const openCount = conversations.filter(c => c.status === "Open").length;
  return <div className="min-h-screen bg-ivory">
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-[264px] flex-col bg-ink px-5 py-7 text-paper transition-transform duration-300 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="relative flex items-center justify-between px-2"><Brand inverse /><button className="lg:hidden" aria-label="Close navigation" onClick={() => setOpen(false)}><X size={20} /></button></div>
      <p className="relative mt-12 px-3 text-[10px] uppercase tracking-[.28em] text-paper/35">Workspace</p>
      <nav className="relative mt-3 space-y-0.5">{links.map(({ href, label, icon: Icon }) => {
        const current = path === href;
        return <Link onClick={() => setOpen(false)} key={href} href={href} className={`relative flex items-center gap-3 rounded-md px-3 py-2.5 text-[14px] transition ${current ? "bg-paper/[.08] text-paper" : "text-paper/55 hover:bg-paper/[.04] hover:text-paper"}`}>
          {current && <span className="absolute -left-5 top-1/2 h-5 w-[2px] -translate-y-1/2 bg-champagne" />}
          <Icon size={17} strokeWidth={1.5} className={current ? "text-champagne" : ""} />{label}
          {href === "/dashboard/inbox" && openCount > 0 && <span className="ml-auto rounded-full bg-champagne/15 px-2 py-0.5 text-[11px] text-champagne">{openCount}</span>}
        </Link>;
      })}</nav>
      <div className="relative mt-8 rounded-lg border border-paper/10 p-4">
        <p className="flex items-center gap-2 text-[13px] text-paper/85"><span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" /><span className="relative h-2 w-2 rounded-full bg-emerald-400" /></span>Concierge is live</p>
        <p className="mt-1.5 text-[12px] leading-5 text-paper/45">Answering on the public site in deterministic demo mode.</p>
      </div>
      <div className="relative mt-auto space-y-1">
        <Link href="/" className="flex items-center gap-3 rounded-md px-3 py-2.5 text-[13px] text-paper/55 hover:bg-paper/[.04] hover:text-paper"><ArrowUpRight size={16} strokeWidth={1.5} />View public site</Link>
        <button onClick={resetDemo} className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-[13px] text-paper/55 hover:bg-paper/[.04] hover:text-paper"><RotateCcw size={16} strokeWidth={1.5} />Reset demo data</button>
        <p className="border-t border-paper/10 px-3 pt-5 text-[11px] leading-5 text-paper/35">Concept demonstration. Simulated CRM, assignment and handoff; data stays in this browser.</p>
      </div>
    </aside>
    {open && <button aria-label="Close navigation" onClick={() => setOpen(false)} className="fixed inset-0 z-40 bg-ink/40 lg:hidden" />}
    <div className="lg:pl-[264px]">
      <header className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-hairline bg-ivory/85 px-5 backdrop-blur-xl sm:px-10">
        <div className="flex items-center gap-4">
          <button onClick={() => setOpen(true)} aria-label="Open navigation" className="rounded-md p-2 hover:bg-linen lg:hidden"><Menu size={20} /></button>
          <p className="text-[11px] uppercase tracking-[.24em] text-charcoal/45"><span className="hidden sm:inline">Staff workspace&nbsp;&nbsp;/&nbsp;&nbsp;</span><span className="text-ink">{active}</span></p>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block"><p className="text-[13px] font-medium text-ink">Demo Manager</p><p className="text-[11px] text-charcoal/50">demo@iwp.local</p></div>
          <span className="grid h-10 w-10 place-items-center rounded-full bg-ink font-serif text-lg text-champagne">DM</span>
        </div>
      </header>
      <main className="px-4 py-8 sm:px-10 sm:py-10">{children}</main>
    </div>
  </div>;
}

/** Shared page heading for workspace screens. */
export function PageHeading({ eyebrow, title, copy, action }: { eyebrow: string; title: string; copy?: string; action?: React.ReactNode }) {
  return <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
    <div>
      <p className="eyebrow text-gold">{eyebrow}</p>
      <h1 className="mt-3 font-serif text-[40px] font-light leading-tight text-ink">{title}</h1>
      {copy && <p className="mt-1 text-[14px] text-charcoal/60">{copy}</p>}
    </div>
    {action}
  </div>;
}
