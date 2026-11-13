import { useState } from "react";

import type { Alert, Page } from "../api";
import { AlertsTable } from "../components/tables";
import { Card, Disclaimer, Status } from "../components/ui";
import { fmtInt } from "../format";
import { useApi } from "../hooks";
import { useMeta } from "../meta";

const SORTS = [
  { key: "ref_date", label: "Fecha" },
  { key: "amount", label: "Importe" },
  { key: "risk_score", label: "Riesgo" },
  { key: "indicator", label: "Indicador" },
  { key: "buyer_name", label: "Órgano" },
];

export default function AlertsPage() {
  const meta = useMeta();
  const [indicator, setIndicator] = useState("");
  const [level, setLevel] = useState("");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("ref_date");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const size = 50;
  const alerts = useApi<Page<Alert>>("/alerts", { indicator, level, q: query, sort, order, page, size });
  const pages = alerts.data ? Math.max(1, Math.ceil(alerts.data.total / size)) : 1;

  const hasFilters = Boolean(indicator || level || query);
  const select = "rounded border border-slate-300 px-2 py-1";
  return (
    <div className="space-y-4">
      <Disclaimer />
      <Card
        title={`Alertas${alerts.data ? ` (${fmtInt(alerts.data.total)})` : ""}`}
        actions={
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <select
              className={select}
              value={indicator}
              onChange={(e) => {
                setIndicator(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Todos los indicadores</option>
              {Object.entries(meta.indicators).map(([code, name]) => (
                <option key={code} value={code}>
                  {code} · {name}
                </option>
              ))}
            </select>
            <select
              className={select}
              value={level}
              onChange={(e) => {
                setLevel(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Todos los niveles</option>
              <option value="contrato">Contrato</option>
              <option value="relacion">Relación órgano-empresa</option>
              <option value="organismo">Organismo</option>
            </select>
            <form
              className="flex items-center gap-1"
              onSubmit={(e) => {
                e.preventDefault();
                setQuery(q.trim());
                setPage(1);
              }}
            >
              <input
                className="rounded border border-slate-300 px-2 py-1"
                placeholder="Texto…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <button type="submit" className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">
                Buscar
              </button>
            </form>
            <select
              className={select}
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
            >
              {SORTS.map((s) => (
                <option key={s.key} value={s.key}>
                  Ordenar por {s.label.toLowerCase()}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="rounded border border-slate-300 px-2 py-1"
              onClick={() => {
                setOrder(order === "desc" ? "asc" : "desc");
                setPage(1);
              }}
              title="Cambiar orden"
            >
              {order === "desc" ? "↓" : "↑"}
            </button>
            {hasFilters && (
              <button
                type="button"
                className="rounded border border-slate-300 px-2 py-1 text-slate-600 hover:bg-slate-50"
                onClick={() => {
                  setIndicator("");
                  setLevel("");
                  setQ("");
                  setQuery("");
                  setPage(1);
                }}
              >
                Limpiar
              </button>
            )}
          </div>
        }
      >
        <Status loading={alerts.loading} error={alerts.error} />
        {alerts.data && <AlertsTable alerts={alerts.data.items} />}
        <div className="mt-3 flex items-center justify-end gap-2 text-sm">
          <button
            type="button"
            className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            Anterior
          </button>
          <span className="tabular-nums">
            Página {page} de {pages}
          </span>
          <button
            type="button"
            className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
            disabled={page >= pages}
            onClick={() => setPage(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </Card>
    </div>
  );
}
