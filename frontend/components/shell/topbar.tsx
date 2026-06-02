"use client";

import { useIsFetching } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/jobs": "Jobs",
  "/quality": "Quality",
  "/datasets": "Datasets",
  "/sources": "Sources",
  "/shards": "Shards",
  "/languages": "Languages",
};

export function Topbar() {
  const path = usePathname();
  const fetching = useIsFetching();
  const [clock, setClock] = useState("--:--:--");

  useEffect(() => {
    const tick = () =>
      setClock(
        new Date().toLocaleTimeString("en-GB", { hour12: false, timeZoneName: undefined }),
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const title = TITLES[path] ?? "Control";

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-[var(--hair)] bg-ink-900/70 px-6 backdrop-blur md:px-10 lg:px-14">
      <div className="flex items-center gap-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-faint">
          arc / control /
        </span>
        <span className="font-display text-[15px] font-semibold tracking-tightest text-paper">
          {title}
        </span>
      </div>

      <div className="flex items-center gap-5">
        <div className="hidden items-center gap-2 sm:flex">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              fetching ? "animate-pulseDot bg-signal" : "bg-faint"
            }`}
          />
          <span className="font-mono text-[11px] text-dim">
            {fetching ? "syncing" : "idle"}
          </span>
        </div>
        <span className="rounded-md border border-[var(--hair)] px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-dim">
          dev
        </span>
        <span className="tnum hidden font-mono text-[12px] text-dim sm:inline">{clock}</span>
      </div>
    </header>
  );
}
