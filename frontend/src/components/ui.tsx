import type { ReactNode } from "react";

import { fmtScore } from "../format";

export function Card({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      {(title || actions) && (
        <header className="mb-3 flex items-center justify-between gap-2">
          {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

/** Semáforo de la puntuación de riesgo (0-100). */
export function RiskBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-slate-400">—</span>;
  const tone =
    score >= 66 ? "bg-red-100 text-red-800" : score >= 33 ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800";
  return (
    <span className={`inline-block min-w-[2.5rem] rounded px-2 py-0.5 text-center text-xs font-semibold tabular-nums ${tone}`}>
      {fmtScore(score)}
    </span>
  );
}

export function Status({ loading, error }: { loading: boolean; error: string | null }) {
  if (loading) return <p className="py-6 text-center text-sm text-slate-500">Cargando…</p>;
  if (error) return <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>;
  return null;
}

export function Disclaimer({ text }: { text?: string }) {
  return (
    <p className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
      <strong>Aviso:</strong>{" "}
      {text ??
        "Los indicadores son señales estadísticas de riesgo calculadas sobre datos abiertos de PLACSP. No constituyen prueba ni acusación de irregularidad alguna."}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-4 text-center text-sm text-slate-500">{children}</p>;
}
