import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { Brand } from "@/components/brand";
import { ConciergeChat } from "@/components/concierge-chat";
import { AskButton, DestinationExplorer, SiteNav } from "@/components/landing";

const pillars = [
  { numeral: "I", title: "Listens first", copy: "Every enquiry—whether a wedding, a career or a partnership—is understood before it is routed. No forms, no menus." },
  { numeral: "II", title: "Asks with care", copy: "One gentle question at a time captures destination, guest count, season and style, the way a senior planner would." },
  { numeral: "III", title: "Hands over gracefully", copy: "The right specialist receives a summary, the full conversation and a reference—before they pick up the phone." }
];

const journey = [
  { step: "Welcome", copy: "A warm greeting in English, हिन्दी or Hinglish, available at any hour." },
  { step: "Understand", copy: "Intent is recognised—wedding sales, client servicing, careers, vendors or finance." },
  { step: "Qualify", copy: "Destination, guests, dates and budget are gathered conversationally." },
  { step: "Introduce", copy: "A prepared handoff arrives in the team inbox and lead pipeline." }
];

const prompts = [
  "I’m planning a Jaipur wedding for 250 guests.",
  "Main Udaipur mein shaadi plan kar raha hoon.",
  "I’m a photographer and would love to collaborate.",
  "I’m already a client and need urgent help.",
  "I need a copy of my invoice.",
  "I would like to speak to a person."
];

export default function Home() {
  return (
    <main className="min-h-screen overflow-x-clip bg-ivory">
      <SiteNav />

      {/* Hero */}
      <section className="relative flex min-h-[100svh] items-end overflow-hidden bg-ink text-paper">
        <Image src="/images/wedding-hero.jpg" alt="A palace wedding terrace in Rajasthan at sunset" fill priority sizes="100vw" className="animate-slow-zoom object-cover object-[62%_center]" />
        <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/25 to-ink/45" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink/70 via-ink/10 to-transparent" />
        <div className="relative mx-auto w-full max-w-[1400px] px-6 pb-12 pt-36 lg:px-12 lg:pb-14">
          <div className="max-w-3xl animate-reveal">
            <p className="eyebrow text-champagne">The art of the first welcome</p>
            <h1 className="mt-7 font-serif text-[clamp(3rem,6.4vw,6.25rem)] font-light leading-[.95] tracking-[-.02em]">
              Every grand celebration begins with a <em className="font-light text-champagne">conversation.</em>
            </h1>
            <p className="mt-8 max-w-xl text-[17px] font-light leading-8 text-paper/80">
              A multilingual concierge that welcomes each enquiry with the grace of a seasoned planner—and quietly guides it to the right specialist.
            </p>
            <div className="mt-11 flex flex-wrap gap-4">
              <AskButton className="btn-light">Begin a conversation <ArrowRight size={15} /></AskButton>
              <Link href="/dashboard" className="btn-ghost-light">View the staff workspace</Link>
            </div>
          </div>
          <div className="mt-16 flex flex-wrap items-end justify-between gap-6 border-t border-paper/20 pt-6 text-[11px] uppercase tracking-wide2 text-paper/55">
            <span>English · हिन्दी · Hinglish</span>
            <span className="hidden sm:inline">Independent concept · not an official IWP site</span>
            <a href="#approach" className="flex items-center gap-3 text-paper/80 hover:text-paper">Discover <span className="h-px w-10 bg-paper/60" /></a>
          </div>
        </div>
      </section>

      {/* Statement + pillars */}
      <section id="approach" className="px-6 py-28 lg:px-12 lg:py-40">
        <div className="mx-auto max-w-[1180px]">
          <div className="mx-auto max-w-4xl text-center">
            <p className="ornament justify-center"><span className="eyebrow">Hospitality, extended</span></p>
            <h2 className="mt-10 font-serif text-[clamp(2.25rem,4.6vw,4rem)] font-light leading-[1.12] text-ink">
              For families who plan in generations, not checklists—<em className="text-burgundy">a concierge that listens before it answers.</em>
            </h2>
          </div>
          <div className="mt-24 grid border-t border-hairline md:grid-cols-3">
            {pillars.map((p, i) => (
              <article key={p.title} className={`px-2 py-12 md:px-10 ${i > 0 ? "border-t border-hairline md:border-l md:border-t-0" : ""}`}>
                <span className="font-serif text-2xl italic text-gold">{p.numeral}.</span>
                <h3 className="mt-6 font-serif text-3xl font-normal text-ink">{p.title}</h3>
                <p className="mt-4 text-[15px] font-light leading-7 text-charcoal/70">{p.copy}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Journey, editorial split */}
      <section className="bg-paper px-6 py-28 lg:px-12 lg:py-36">
        <div className="mx-auto grid max-w-[1180px] items-center gap-16 lg:grid-cols-[.85fr_1fr] lg:gap-24">
          <div className="relative mx-auto w-full max-w-[440px]">
            <div className="arch relative aspect-[3/4] overflow-hidden">
              <Image src="/images/wedding-hero.jpg" alt="A couple beneath a floral mandap" fill sizes="(min-width: 1024px) 440px, 90vw" className="scale-[1.9] object-cover object-[71%_62%]" />
            </div>
            <div className="arch pointer-events-none absolute -inset-4 border border-gold/30" />
            <p className="absolute -bottom-10 left-0 right-0 text-center font-serif text-sm italic text-charcoal/50">Rajasthan, imagined — an original AI-generated visual</p>
          </div>
          <div>
            <p className="eyebrow text-gold">The journey of an enquiry</p>
            <h2 className="mt-6 font-serif text-[clamp(2.25rem,4vw,3.5rem)] font-light leading-[1.05] text-ink">From a first hello to a prepared introduction.</h2>
            <ol className="mt-12">
              {journey.map((j, i) => (
                <li key={j.step} className="grid grid-cols-[3.5rem_1fr] gap-4 border-t border-hairline py-6 last:border-b">
                  <span className="font-serif text-xl italic text-gold">0{i + 1}</span>
                  <div>
                    <h3 className="text-[12px] font-medium uppercase tracking-wide2 text-ink">{j.step}</h3>
                    <p className="mt-2 text-[15px] font-light leading-7 text-charcoal/70">{j.copy}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>

      {/* Destinations */}
      <section id="destinations" className="relative bg-ink px-6 py-28 text-paper lg:px-12 lg:py-36">
        <div className="relative mx-auto max-w-[1280px]">
          <div className="mb-16 flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <p className="eyebrow text-champagne">Begin with a feeling</p>
              <h2 className="mt-6 font-serif text-[clamp(2.5rem,5vw,4.5rem)] font-light leading-none">Where will your story unfold?</h2>
            </div>
            <p className="max-w-sm text-[15px] font-light leading-7 text-paper/60">Choose a setting and the concierge will talk you through its atmosphere, scale and seasons.</p>
          </div>
          <DestinationExplorer />
        </div>
      </section>

      {/* Try the concierge */}
      <section id="concierge" className="px-6 py-28 lg:px-12 lg:py-36">
        <div className="mx-auto grid max-w-[1180px] gap-16 lg:grid-cols-[.9fr_1.1fr] lg:items-start">
          <div className="lg:sticky lg:top-32">
            <p className="eyebrow text-gold">An open invitation</p>
            <h2 className="mt-6 font-serif text-[clamp(2.5rem,5vw,4.25rem)] font-light leading-[1.02] text-ink">Try a real conversation.</h2>
            <p className="mt-7 max-w-md text-[15px] font-light leading-7 text-charcoal/70">Choose a sample question—or write your own—and watch the concierge recognise intent, ask a considered follow-up and prepare a handoff. Each handed-off conversation appears in the staff workspace.</p>
            <div className="mt-10 flex flex-wrap gap-4">
              <AskButton className="btn-dark">Open the concierge <ArrowRight size={15} /></AskButton>
              <Link href="/dashboard/inbox" className="btn-outline">See the team inbox</Link>
            </div>
          </div>
          <div className="border-t border-ink/80">
            <p className="flex items-center justify-between py-5 text-[11px] uppercase tracking-wide2 text-charcoal/55"><span>Sample questions</span><span>Six routes</span></p>
            {prompts.map((q) => (
              <AskButton key={q} prompt={q} className="group flex w-full items-center justify-between gap-6 border-t border-hairline py-6 text-left">
                <span className="font-serif text-2xl font-light text-ink transition group-hover:translate-x-2 group-hover:text-burgundy">“{q}”</span>
                <ArrowUpRight size={18} className="shrink-0 text-gold transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </AskButton>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-umber px-6 pb-10 pt-20 text-paper lg:px-12">
        <div className="mx-auto max-w-[1280px]">
          <div className="flex flex-col items-center text-center">
            <Brand inverse centered />
            <p className="mt-10 max-w-2xl font-serif text-2xl font-light italic leading-snug text-paper/80">“The most memorable celebrations are remembered for how every guest was made to feel—beginning with the very first message.”</p>
          </div>
          <div className="mt-20 grid gap-10 border-t border-paper/15 pt-10 text-[13px] font-light leading-6 text-paper/55 md:grid-cols-3">
            <div><p className="eyebrow mb-3 text-champagne">About this concept</p>An independent portfolio concept exploring how an AI concierge might support a luxury wedding-planning house. Not affiliated with, endorsed by or operated by Indian Wedding Planners.</div>
            <div><p className="eyebrow mb-3 text-champagne">How the demo works</p>Deterministic, rule-based routing runs entirely in your browser. No API key, sign-up or live team is involved, and all people and leads are fictional.</div>
            <div className="md:text-right"><p className="eyebrow mb-3 text-champagne">Explore</p>
              <Link href="/dashboard" className="inline-flex items-center gap-2 text-paper/80 hover:text-paper">Staff workspace <ArrowUpRight size={14} /></Link><br />
              <a href="#concierge" className="inline-flex items-center gap-2 text-paper/80 hover:text-paper">Try the concierge <ArrowUpRight size={14} /></a>
            </div>
          </div>
          <p className="mt-14 text-center text-[10px] uppercase tracking-luxe text-paper/35">Independent concept demonstration · Not an official IWP deployment</p>
        </div>
      </footer>

      <ConciergeChat />
    </main>
  );
}
