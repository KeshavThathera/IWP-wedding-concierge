"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { Brand } from "./brand";
import { askConcierge } from "./concierge-chat";

export function SiteNav() {
  const [solid, setSolid] = useState(false);
  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  const link = `hidden whitespace-nowrap text-[11px] font-medium uppercase tracking-wide2 transition lg:block ${solid ? "text-charcoal/70 hover:text-ink" : "text-paper/80 hover:text-paper"}`;
  return (
    <nav className={`fixed inset-x-0 top-0 z-30 transition-all duration-500 ${solid ? "border-b border-hairline bg-paper/90 py-3 backdrop-blur-xl" : "bg-transparent py-6"}`}>
      <div className="mx-auto grid max-w-[1400px] grid-cols-[1fr_auto_1fr] items-center px-6 lg:px-12">
        <div className="flex items-center gap-9">
          <a href="#approach" className={link}>The approach</a>
          <a href="#destinations" className={link}>Destinations</a>
          <a href="#concierge" className={link}>Concierge</a>
        </div>
        <Brand inverse={!solid} />
        <div className="flex justify-end">
          <Link href="/dashboard" className={`group inline-flex items-center gap-2 border-b pb-1 text-[11px] font-medium uppercase tracking-wide2 transition ${solid ? "border-ink/30 text-ink hover:border-ink" : "border-paper/40 text-paper hover:border-paper"}`}>
            <span className="hidden sm:inline">Staff workspace</span><span className="sm:hidden">Staff</span>
            <ArrowUpRight size={14} className="transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
          </Link>
        </div>
      </div>
    </nav>
  );
}

export function AskButton({ prompt, className, children }: { prompt?: string; className?: string; children: React.ReactNode }) {
  return <button type="button" onClick={() => askConcierge(prompt)} className={className}>{children}</button>;
}

const destinations = [
  { city: "Udaipur", region: "Rajasthan", note: "Lakeside palaces, sunset terraces and quiet, intimate grandeur.", position: "15% 60%" },
  { city: "Jaipur", region: "Rajasthan", note: "Pink-city courtyards, heritage havelis and celebrations at a royal scale.", position: "62% 30%" },
  { city: "Jodhpur", region: "Rajasthan", note: "Blue-city fort ramparts for dramatic, desert-edge evenings.", position: "95% 45%" },
  { city: "Goa", region: "West coast", note: "Barefoot ceremonies, sunlit coastlines and relaxed multi-day festivities.", position: "40% 85%" }
];

export function DestinationExplorer() {
  const [active, setActive] = useState(0);
  return (
    <div className="grid gap-12 lg:grid-cols-[1fr_.9fr] lg:gap-20">
      <ol className="border-t border-paper/15">
        {destinations.map((d, i) => (
          <li key={d.city} onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} className="border-b border-paper/15">
            <button type="button" onClick={() => { setActive(i); askConcierge(`Tell me about planning a wedding in ${d.city}.`); }} className="group grid w-full grid-cols-[3rem_1fr_auto] items-baseline gap-4 py-7 text-left sm:py-8">
              <span className={`font-serif text-lg italic transition ${active === i ? "text-champagne" : "text-paper/35"}`}>0{i + 1}</span>
              <span>
                <span className={`block font-serif text-4xl font-light transition duration-500 sm:text-5xl ${active === i ? "translate-x-2 text-paper" : "text-paper/55"}`}>{d.city}</span>
                <span className={`mt-3 block max-w-md text-sm leading-6 text-paper/55 transition-all duration-500 ${active === i ? "max-h-20 opacity-100" : "max-h-0 overflow-hidden opacity-0 lg:max-h-0"}`}>{d.note}</span>
              </span>
              <span className={`hidden items-center gap-2 text-[10px] font-medium uppercase tracking-wide2 transition sm:flex ${active === i ? "text-champagne" : "text-paper/30"}`}>
                Ask <ArrowRight size={13} className="transition group-hover:translate-x-1" />
              </span>
            </button>
          </li>
        ))}
      </ol>
      <div className="relative hidden lg:block">
        <div className="arch relative h-[560px] overflow-hidden">
          <Image src="/images/wedding-hero.jpg" alt="" fill sizes="(min-width: 1024px) 40vw, 0px" className="scale-[1.35] object-cover transition-[object-position] duration-[1400ms] ease-out" style={{ objectPosition: destinations[active].position }} />
          <div className="absolute inset-0 bg-gradient-to-t from-ink/70 via-transparent to-transparent" />
          <div className="absolute inset-x-0 bottom-0 p-8 text-center">
            <p className="eyebrow text-champagne">{destinations[active].region}</p>
            <p className="mt-2 font-serif text-3xl font-light italic text-paper">{destinations[active].city}</p>
          </div>
        </div>
        <div className="arch pointer-events-none absolute -inset-3 border border-champagne/25" />
      </div>
    </div>
  );
}
