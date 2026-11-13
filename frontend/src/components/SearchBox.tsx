import { useEffect, useState } from "react";

import { get, type SearchResult } from "../api";
import { fmtEurShort } from "../format";

/** Búsqueda por nombre o NIF de órganos y empresas. */
export default function SearchBox({
  onSelect,
  placeholder = "Buscar órgano o empresa por nombre o NIF…",
}: {
  onSelect: (r: SearchResult) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      get<SearchResult[]>("/search", { q: q.trim(), limit: 12 })
        .then((r) => {
          setResults(r);
          setOpen(true);
        })
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [q]);

  return (
    <div className="relative w-full max-w-xl">
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
      />
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-80 w-full overflow-auto rounded-md border border-slate-200 bg-white text-sm shadow-lg">
          {results.map((r) => (
            <li key={`${r.kind}-${r.id}`}>
              <button
                type="button"
                className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-slate-50"
                onMouseDown={() => {
                  onSelect(r);
                  setQ("");
                  setOpen(false);
                }}
              >
                <span>
                  <span
                    className={`mr-2 rounded px-1.5 py-0.5 text-xs ${r.kind === "buyer" ? "bg-sky-100 text-sky-800" : "bg-violet-100 text-violet-800"}`}
                  >
                    {r.kind === "buyer" ? "Órgano" : "Empresa"}
                  </span>
                  {r.name}
                  {r.nif && <span className="ml-1 text-xs text-slate-500">{r.nif}</span>}
                </span>
                <span className="whitespace-nowrap text-xs text-slate-500">{fmtEurShort(r.amount)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
