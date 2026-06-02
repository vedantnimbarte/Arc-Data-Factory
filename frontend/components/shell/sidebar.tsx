"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string; code: string };

const SECTIONS: { title: string; items: Item[] }[] = [
  {
    title: "Monitor",
    items: [
      { href: "/", label: "Overview", code: "00" },
      { href: "/jobs", label: "Jobs", code: "01" },
      { href: "/quality", label: "Quality", code: "02" },
    ],
  },
  {
    title: "Catalog",
    items: [
      { href: "/datasets", label: "Datasets", code: "03" },
      { href: "/sources", label: "Sources", code: "04" },
      { href: "/shards", label: "Shards", code: "05" },
      { href: "/languages", label: "Languages", code: "06" },
    ],
  },
];

export function Sidebar() {
  const path = usePathname();

  return (
    <aside className="sticky top-0 hidden h-screen w-[244px] shrink-0 flex-col border-r border-[var(--hair)] bg-ink-900/60 backdrop-blur md:flex">
      <div className="flex items-center gap-3 px-6 py-6">
        <span className="grid h-8 w-8 place-items-center rounded-md bg-signal text-ink-900 shadow-glow">
          <span className="font-display text-lg font-extrabold leading-none">A</span>
        </span>
        <div className="leading-tight">
          <div className="font-display text-[15px] font-bold tracking-tightest text-paper">
            ARC Factory
          </div>
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            data control
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-7 px-3 py-4">
        {SECTIONS.map((section) => (
          <div key={section.title}>
            <div className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.22em] text-faint">
              {section.title}
            </div>
            <div className="space-y-0.5">
              {section.items.map((it) => {
                const active = path === it.href;
                return (
                  <Link
                    key={it.href}
                    href={it.href}
                    className={`group flex items-center gap-3 rounded-md px-3 py-2 text-[13.5px] transition-colors ${
                      active
                        ? "bg-ink-700 text-paper"
                        : "text-dim hover:bg-ink-800 hover:text-paper"
                    }`}
                  >
                    <span
                      className={`h-3.5 w-[2px] rounded-full transition-colors ${
                        active ? "bg-signal" : "bg-transparent group-hover:bg-faint"
                      }`}
                    />
                    <span className="font-mono text-[10px] text-faint">{it.code}</span>
                    <span className="font-medium">{it.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-[var(--hair)] px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-ok" />
          <span className="font-mono text-[11px] text-dim">pipeline online</span>
        </div>
        <div className="mt-1 font-mono text-[10px] text-faint">v0.1.0 · 9 stages</div>
      </div>
    </aside>
  );
}
