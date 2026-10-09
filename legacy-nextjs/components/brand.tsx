import Link from "next/link";

export function Monogram({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden className={className}>
      <circle cx="20" cy="20" r="19" fill="none" stroke="currentColor" strokeOpacity=".45" strokeWidth=".75" />
      <circle cx="20" cy="20" r="15.5" fill="none" stroke="currentColor" strokeOpacity=".25" strokeWidth=".5" />
      <path d="M20 9.5 L22.2 20 L20 30.5 L17.8 20 Z" fill="currentColor" fillOpacity=".9" />
      <path d="M9.5 20 L20 18.6 L30.5 20 L20 21.4 Z" fill="currentColor" fillOpacity=".45" />
    </svg>
  );
}

export function Brand({ inverse = false, centered = false }: { inverse?: boolean; centered?: boolean }) {
  return (
    <Link href="/" className={`group flex items-center gap-3 ${centered ? "flex-col gap-1.5 text-center" : ""} ${inverse ? "text-paper" : "text-ink"}`}>
      <Monogram className={`h-9 w-9 shrink-0 ${inverse ? "text-champagne" : "text-gold"}`} />
      <span className="whitespace-nowrap leading-none">
        <strong className="block font-serif text-[22px] font-medium tracking-[.34em]">IWP</strong>
        <span className={`mt-1 block text-[9px] font-medium uppercase tracking-luxe ${inverse ? "text-paper/60" : "text-charcoal/50"}`}>The Wedding Concierge</span>
      </span>
    </Link>
  );
}
