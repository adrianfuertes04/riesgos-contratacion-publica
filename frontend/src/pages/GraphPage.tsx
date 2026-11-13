import { useCallback, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { enc, type BuyerSummary, type Graph, type GraphNode } from "../api";
import EChart, { type ECElementEvent, type EChartHandle, type EChartsOption } from "../components/EChart";
import SearchBox from "../components/SearchBox";
import { Card, Disclaimer, Empty, RiskBadge, Status } from "../components/ui";
import { fmtEur, fmtEurShort, fmtInt } from "../format";
import { useApi } from "../hooks";

const FILTERS = ["depth", "year", "min_amount", "cpv", "nuts", "min_risk"] as const;

function riskColor(score: number | null, kind: GraphNode["kind"]) {
  if (score == null) return kind === "buyer" ? "#0ea5e9" : "#a78bfa";
  if (score >= 66) return "#dc2626";
  if (score >= 33) return "#f59e0b";
  return kind === "buyer" ? "#0ea5e9" : "#a78bfa";
}

export default function GraphPage() {
  const [params, setParams] = useSearchParams();
  const node = params.get("node");
  const query = Object.fromEntries(FILTERS.map((f) => [f, params.get(f)]));
  const graph = useApi<Graph>(node ? "/graph" : null, { node, limit: 25, ...query });
  const examples = useApi<BuyerSummary[]>(!node ? "/buyers" : null, { limit: 5 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const chartRef = useRef<EChartHandle>(null);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };

  const hasFilters = FILTERS.some((f) => Boolean(params.get(f)));
  const clearFilters = () => {
    const next = new URLSearchParams();
    if (node) next.set("node", node);
    setParams(next);
  };

  const option = useMemo<EChartsOption>(() => {
    const g = graph.data;
    if (!g) return {};
    const maxAmount = Math.max(1, ...g.nodes.map((n) => n.amount ?? 0));
    const maxEdge = Math.max(1, ...g.edges.map((e) => e.amount ?? 0));
    return {
      tooltip: {
        confine: true,
        formatter: (p) => {
          const d = (p as unknown as { dataType: string; data: Record<string, unknown> }).data;
          if ((p as unknown as { dataType: string }).dataType === "edge") {
            return `${fmtInt(d.n_contracts as number)} contratos · ${fmtEur(d.amount as number)}<br/>Alertas: ${d.n_flags}`;
          }
          return `<b>${d.label_text}</b><br/>${d.kind === "buyer" ? "Órgano" : "Empresa"} · ${fmtEur(d.amount as number)}`;
        },
      },
      legend: [{ data: ["Órgano", "Empresa"], top: 0 }],
      series: [
        {
          type: "graph",
          layout: "force",
          roam: true,
          draggable: true,
          force: { repulsion: 280, edgeLength: [70, 170], gravity: 0.08 },
          categories: [{ name: "Órgano", itemStyle: { color: "#0ea5e9" } }, { name: "Empresa", itemStyle: { color: "#a78bfa" } }],
          label: { show: g.nodes.length <= 40, position: "right", fontSize: 10, formatter: "{b}" },
          lineStyle: { color: "source", opacity: 0.5, curveness: 0.1 },
          emphasis: { focus: "adjacency" },
          data: g.nodes.map((n) => ({
            id: n.id,
            name: (n.name ?? n.ref).slice(0, 40),
            label_text: n.name ?? n.ref,
            kind: n.kind,
            amount: n.amount,
            category: n.kind === "buyer" ? 0 : 1,
            symbol: n.kind === "buyer" ? "rect" : "circle",
            symbolSize: 10 + 30 * Math.sqrt((n.amount ?? 0) / maxAmount),
            itemStyle: {
              color: riskColor(n.risk_score, n.kind),
              borderColor: n.ref === node?.split(":").slice(1).join(":") ? "#0f172a" : "#fff",
              borderWidth: 2,
            },
          })),
          links: g.edges.map((e) => ({
            source: e.source,
            target: e.target,
            n_contracts: e.n_contracts,
            amount: e.amount,
            n_flags: e.n_flags,
            lineStyle: { width: 1 + 6 * Math.sqrt((e.amount ?? 0) / maxEdge), color: e.n_flags > 0 ? "#f87171" : "#94a3b8" },
          })),
        },
      ],
    };
  }, [graph.data, node]);

  const onClick = useCallback((p: ECElementEvent) => {
    if (p.dataType === "node") setSelectedId((p.data as { id: string }).id);
  }, []);

  const selected = graph.data?.nodes.find((n) => n.id === selectedId) ?? null;
  const selectedEdges = graph.data?.edges.filter((e) => e.source === selectedId || e.target === selectedId) ?? [];

  return (
    <div className="space-y-4">
      <Disclaimer />
      <div className="flex flex-wrap items-end gap-3">
        <SearchBox
          placeholder="Centrar el grafo en un órgano o empresa…"
          onSelect={(r) => {
            setSelectedId(null);
            setParam("node", `${r.kind}:${r.id}`);
          }}
        />
        <label className="text-sm">
          Profundidad
          <select
            className="ml-1 rounded border border-slate-300 px-2 py-1"
            value={params.get("depth") ?? "1"}
            onChange={(e) => setParam("depth", e.target.value)}
          >
            <option value="1">1 salto</option>
            <option value="2">2 saltos</option>
          </select>
        </label>
        {[
          { key: "year", label: "Año", width: "w-20" },
          { key: "min_amount", label: "Importe mín. (€)", width: "w-28" },
          { key: "cpv", label: "División CPV", width: "w-16" },
          { key: "nuts", label: "NUTS", width: "w-20" },
          { key: "min_risk", label: "Riesgo mín.", width: "w-16" },
        ].map((f) => (
          <label key={f.key} className="text-sm">
            {f.label}
            <input
              key={`${f.key}-${params.get(f.key) ?? ""}`}
              className={`ml-1 rounded border border-slate-300 px-2 py-1 ${f.width}`}
              defaultValue={params.get(f.key) ?? ""}
              onBlur={(e) => setParam(f.key, e.target.value.trim())}
              onKeyDown={(e) => e.key === "Enter" && setParam(f.key, e.currentTarget.value.trim())}
            />
          </label>
        ))}
        {hasFilters && (
          <button
            type="button"
            className="rounded border border-slate-300 px-2.5 py-1 text-sm text-slate-600 hover:bg-slate-50"
            onClick={clearFilters}
          >
            Limpiar filtros
          </button>
        )}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card
            title="Red de adjudicaciones"
            actions={
              graph.data && (
                <div className="flex items-center gap-1 text-xs">
                  <button
                    type="button"
                    className="rounded border border-slate-300 px-2 py-0.5 hover:bg-slate-50"
                    onClick={() => chartRef.current?.zoom(1.3)}
                    title="Acercar"
                  >
                    +
                  </button>
                  <button
                    type="button"
                    className="rounded border border-slate-300 px-2 py-0.5 hover:bg-slate-50"
                    onClick={() => chartRef.current?.zoom(0.75)}
                    title="Alejar"
                  >
                    −
                  </button>
                  <button
                    type="button"
                    className="rounded border border-slate-300 px-2 py-0.5 hover:bg-slate-50"
                    onClick={() => chartRef.current?.reset()}
                    title="Restablecer vista"
                  >
                    Restablecer
                  </button>
                </div>
              )
            }
          >
            {!node && (
              <div className="space-y-3 py-4 text-center">
                <Empty>Busca un órgano o una empresa para ver su red de adjudicaciones.</Empty>
                {examples.data && examples.data.length > 0 && (
                  <div className="flex flex-wrap justify-center gap-2 text-xs">
                    <span className="self-center text-slate-500">Ejemplos:</span>
                    {examples.data.map((b) => (
                      <button
                        key={b.buyer_id}
                        type="button"
                        className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-700 hover:border-sky-300 hover:bg-sky-50"
                        onClick={() => {
                          setSelectedId(null);
                          setParam("node", `buyer:${b.buyer_id}`);
                        }}
                      >
                        {(b.name ?? b.buyer_id).slice(0, 36)} ({fmtEurShort(b.amount)})
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            <Status loading={graph.loading} error={graph.error} />
            {graph.data && <EChart ref={chartRef} option={option} height={600} onClick={onClick} />}
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
              <span>Aristas rojas: relaciones con señales de riesgo · Rueda o botones para zoom.</span>
              {graph.data?.truncated && <span>Subgrafo recortado a las relaciones de mayor importe.</span>}
            </div>
          </Card>
        </div>
        <Card title="Nodo seleccionado">
          {!selected && <Empty>Pulsa un nodo del grafo.</Empty>}
          {selected && (
            <div className="space-y-3 text-sm">
              <div className="font-medium">{selected.name}</div>
              <dl className="grid grid-cols-2 gap-2">
                <dt className="text-slate-500">Tipo</dt>
                <dd className="text-right">{selected.kind === "buyer" ? "Órgano de contratación" : "Empresa"}</dd>
                <dt className="text-slate-500">Identificador</dt>
                <dd className="break-all text-right font-mono text-xs">{selected.ref}</dd>
                <dt className="text-slate-500">Contratos</dt>
                <dd className="text-right tabular-nums">{fmtInt(selected.n_contracts)}</dd>
                <dt className="text-slate-500">Importe total</dt>
                <dd className="text-right tabular-nums">{fmtEur(selected.amount)}</dd>
                <dt className="text-slate-500">Riesgo</dt>
                <dd className="text-right">
                  <RiskBadge score={selected.risk_score} />
                </dd>
                <dt className="text-slate-500">Alertas en las relaciones visibles</dt>
                <dd className="text-right tabular-nums">{fmtInt(selectedEdges.reduce((s, e) => s + e.n_flags, 0))}</dd>
              </dl>
              <div className="flex gap-2">
                <Link
                  className="rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white"
                  to={selected.kind === "buyer" ? `/organismos/${enc(selected.ref)}` : `/empresas/${enc(selected.ref)}`}
                >
                  Abrir ficha
                </Link>
                <button
                  type="button"
                  className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium"
                  onClick={() => setParam("node", `${selected.kind}:${selected.ref}`)}
                >
                  Centrar aquí
                </button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
