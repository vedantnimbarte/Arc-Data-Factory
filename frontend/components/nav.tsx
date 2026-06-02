import Link from "next/link";

const PAGES = [
  ["/", "Overview"],
  ["/datasets", "Datasets"],
  ["/sources", "Sources"],
  ["/jobs", "Jobs"],
  ["/languages", "Languages"],
  ["/quality", "Quality"],
  ["/shards", "Shards"],
];

export function Nav() {
  return (
    <nav className="flex flex-col gap-1 p-4 w-52 shrink-0 border-r border-white/10">
      <div className="text-accent font-bold text-lg mb-4">ARC Data Factory</div>
      {PAGES.map(([href, label]) => (
        <Link
          key={href}
          href={href}
          className="px-3 py-2 rounded hover:bg-white/5 text-sm text-gray-300"
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
